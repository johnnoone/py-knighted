from __future__ import annotations

import asyncio
import concurrent.futures
import logging
from abc import ABCMeta
from collections import ChainMap
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from inspect import signature, unwrap
from itertools import chain
from types import MappingProxyType
from typing import Callable, Optional, cast
from weakref import WeakKeyDictionary

from cached_property import cached_property

logger = logging.getLogger("knighted")

MaybeInjector = Optional["Injector"]
ANNOTATIONS: WeakKeyDictionary[Callable, "Annotation"] = WeakKeyDictionary()

current_injector_var: ContextVar[MaybeInjector] = ContextVar("current_injector")


def current_injector() -> MaybeInjector:
    global current_injector_var
    return current_injector_var.get(None)


def annotate(*pos_notes, **kw_notes):
    def wrapper(func):
        func = unwrap(func)
        ANNOTATIONS[func] = Annotation(func, pos_notes, kw_notes)
        return func

    for arg in chain(pos_notes, kw_notes.values()):
        if not isinstance(arg, str):
            raise ValueError("Notes must be strings")

    return wrapper


class Annotation:
    def __init__(self, func, pos_notes, kw_notes):
        self.bind_partial = signature(func).bind_partial
        self.is_coro = asyncio.iscoroutinefunction(func)
        self.markers = self.bind_partial(*pos_notes, **kw_notes).arguments

    def given(self, *args, **kwargs):
        return list(self.bind_partial(*args, **kwargs).arguments)


class DataProxy:
    def __init__(self):
        self.data = WeakKeyDictionary()

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        if instance is None:
            response = self.data.setdefault(owner, {})
        else:
            response = self.data.setdefault(
                instance, ChainMap({}, MappingProxyType(getattr(owner, self.name)))
            )
        return response


class FactoryAccessor:
    def __get__(self, instance, owner):
        def wrap_name(name, func=None, *, singleton=True):
            def wrap_func(func):
                (instance or owner).factories[name] = func, singleton
                return func

            if func:
                return wrap_func(func)
            return wrap_func

        return wrap_name


def close_reaction(obj):
    obj.close()


class CloseHandler:
    """Closes mounted services
    """

    def __init__(self, injector):
        self.injector = injector
        self.registry = WeakKeyDictionary()

    def register(self, obj, reaction=None):
        """Register callbacks that should be thrown on close.
        """
        reaction = reaction or close_reaction
        reactions = self.registry.setdefault(obj, set())
        reactions.add(reaction)

    def unregister(self, obj, reaction=None):
        """Unregister callbacks that should not be thrown on close.
        """
        if reaction:
            reactions = self.registry.setdefault(obj, set())
            reactions.remove(reaction)
            if not reactions:
                self.registry.pop(obj, None)
        else:
            self.registry.pop(obj, None)

    def __call__(self):
        for obj, reactions in self.registry.items():
            for reaction in reactions:
                reaction(obj)
        self.injector.services.clear()


class Injector(metaclass=ABCMeta):
    factory = FactoryAccessor()
    factories = DataProxy()
    services = DataProxy()

    def __init__(self):
        self.close = CloseHandler(self)

    def refresh(self, name: str):
        service = self.services.pop(name, None)
        if service:
            logger.info("Refreshed service=%s", name)
        return service

    @cached_property
    def executor(self):
        return concurrent.futures.ThreadPoolExecutor(max_workers=10)

    def get(self, name: str) -> asyncio.Future:
        future: asyncio.Future = asyncio.Future()
        try:
            result = self.services[name]
            future.set_result(result)
        except KeyError:
            for fact, args in note_loop(name):
                if fact in self.factories:
                    func, singleton = self.factories[fact]
                    if asyncio.iscoroutinefunction(func):
                        task = asyncio.create_task(func(*args))
                    else:
                        loop = asyncio.get_running_loop()
                        task = cast(
                            asyncio.Task,
                            loop.run_in_executor(self.executor, func, *args),
                        )
                    break
            else:
                raise ValueError("%r is not defined" % name)
            logger.info("Loading service=%s", name)
            if singleton:
                task.add_done_callback(
                    lambda x: self.services.update({name: x.result()})
                )
            task.add_done_callback(lambda x: future.set_result(x.result()))
        return future

    def set(self, name: str, value):
        self.services[name] = value

    def __getitem__(self, name: str):
        return self.get(name)

    def __setitem__(self, name: str, value):
        self.set(name, value)

    def apply(self, *args, **kwargs) -> asyncio.Future:
        with self.auto():
            func, *args = args  # type: ignore
            orig = unwrap(func)
            anno = ANNOTATIONS.get(orig)
            if anno:
                return self.do_apply(func, anno, args, kwargs)
            fut: asyncio.Future = asyncio.Future()
            fut.set_result(func(*args, **kwargs))
            return fut

    def do_apply(self, func, anno, args, kwargs):
        given = anno.given(*args, **kwargs)
        services = {
            key: self.get(service)
            for key, service in anno.markers.items()
            if key not in given
        }
        logger.info("Apply services=%s to func=%r", ",".join(services.keys()), func)

        async def run(args, kwargs):
            kwargs = dict(kwargs)
            for k, v in services.items():
                kwargs[k] = await v
            result = func(*args, **kwargs)
            if anno.is_coro:
                result = await result
            return result

        return asyncio.create_task(run(args, kwargs))

    def partial(self, func):
        orig = unwrap(func)
        anno = ANNOTATIONS.get(orig)
        if anno:

            @wraps(func)
            def parted(*args, **kwargs):
                return self.do_apply(func, anno, args, kwargs)

            return parted
        return func

    @contextmanager
    def auto(self):
        token = current_injector_var.set(self)
        try:
            yield self
        finally:
            current_injector_var.reset(token)


class attr:
    def __init__(self, name):
        self.service_name = name

    def __get__(self, obj, objtype):
        if obj is None:
            raise AttributeError("attr applies to instances only")
        return current_injector_var.get().get(self.service_name)


def note_loop(note):
    args = note.split(":")
    results = []
    fact, *args = args
    results.append((fact, args))
    while args:
        suffix, *args = args
        fact = "%s:%s" % (fact, suffix)
        results.append((fact, args))
    for fact, args in sorted(results, reverse=True):
        yield fact, args

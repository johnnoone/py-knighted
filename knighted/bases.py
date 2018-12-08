from __future__ import annotations

import asyncio
import concurrent.futures
import logging
from abc import ABCMeta
from collections import OrderedDict, defaultdict
from functools import wraps
from inspect import signature
from itertools import chain
from weakref import WeakKeyDictionary

from cached_property import cached_property

logger = logging.getLogger("knighted")


class Factory:

    def __init__(self, target):
        self.target = target

    def __call__(self, note, func=None):
        def decorate(func):
            self.target.factories[note] = func
            return func
        if func:
            return decorate(func)
        return decorate


class FactoryMethod:
    """Decorator for func
    """

    def __get__(self, obj, objtype):
        target = obj or objtype
        return Factory(target)


class DataProxy:

    def __init__(self, name, type):
        self.name = name
        self.type = type

    def __get__(self, obj, objtype):
        target = obj or objtype
        if not hasattr(target, self.name):
            setattr(target, self.name, self.type())
        return getattr(target, self.name)


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
    """Collects dependencies and reads annotations to inject them.
    """

    factory = FactoryMethod()
    services = DataProxy('_services', OrderedDict)
    factories = DataProxy('_factories', OrderedDict)

    def __init__(self):
        self.services = self.__class__.services.copy()
        self.factories = self.__class__.factories.copy()
        self.reactions = defaultdict(WeakKeyDictionary)
        self.close = CloseHandler(self)

    @cached_property
    def executor(self):
        return concurrent.futures.ThreadPoolExecutor(max_workers=10)

    async def get(self, note):
        if note in self.services:
            return self.services[note]

        for fact, args in note_loop(note):
            if fact in self.factories:
                func = self.factories[fact]
                if asyncio.iscoroutinefunction(func):
                    instance = await func(*args)
                else:
                    loop = asyncio.get_running_loop()
                    instance = await loop.run_in_executor(self.executor, func, *args)
                logger.info('loaded service %s' % note)
                self.services[note] = instance
                return instance
        raise ValueError('%r is not defined' % note)

    async def apply(self, *args, **kwargs):
        func, *args = args
        response = await self.partial(func)(*args, **kwargs)
        return response

    def partial(self, func):
        """Resolves lately dependencies.

        Returns:
            callable: the service partially resolved
        """

        @wraps(func)
        async def wrapper(*args, **kwargs):
            if func in ANNOTATIONS:
                annotation = ANNOTATIONS[func]
                given = annotation.given(*args, **kwargs)
                to_load = {}
                for key, note in annotation.marked.items():
                    if key not in given:
                        to_load[key] = asyncio.create_task(self.get(note))
                for key, fut in to_load.items():
                    to_load[key] = await fut
                kwargs.update(to_load)
                result = func(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    result = await result
                return result
            logger.warning('%r is not annoted', func)
            return func(*args, **kwargs)
        return wrapper


class Annotation:
    def __init__(self, pos_notes, kw_notes, func):
        self.pos_notes = pos_notes
        self.kw_notes = kw_notes
        self.bind_partial = signature(func).bind_partial

    @cached_property
    def marked(self):
        return self.bind_partial(*self.pos_notes, **self.kw_notes).arguments

    def given(self, *args, **kwargs):
        return list(self.bind_partial(*args, **kwargs).arguments)


ANNOTATIONS: WeakKeyDictionary[str, Annotation] = WeakKeyDictionary()


def close_reaction(obj):
    obj.close()


def annotate(*args, **kwargs):

    def decorate(func):
        ANNOTATIONS[func] = Annotation(args, kwargs, func)
        return func

    for arg in chain(args, kwargs.values()):
        if not isinstance(arg, str):
            raise ValueError('Notes must be strings')

    return decorate


def note_loop(note):
    args = note.split(':')
    results = []
    fact, *args = args
    results.append((fact, args))
    while args:
        suffix, *args = args
        fact = '%s:%s' % (fact, suffix)
        results.append((fact, args))
    for fact, args in sorted(results, reverse=True):
        yield fact, args

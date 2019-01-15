import pytest

from knighted import Injector, annotate, attr, AnnotationError
from typing import Any


@pytest.fixture
def services():
    class MyInjector(Injector):
        pass

    return MyInjector()


@pytest.mark.asyncio
async def test_annotate_class(services):
    @services.factory("foo")
    def foo_factory():
        return "I am foo"

    @annotate
    class Tic:
        foo: Any = attr("foo")

        def __call__(self):
            return {"foo": self.foo}

    result = await services.apply(Tic)

    assert result() == {"foo": "I am foo"}


@pytest.mark.asyncio
async def test_annotate_parent_class_is_illegal(services):
    with pytest.raises(AnnotationError):

        @annotate("foo")
        class Tic:
            def __init__(self, foo):
                self.foo = foo

            def __call__(self):
                return {"foo": self.foo}


@pytest.mark.asyncio
async def test_annotate_subclassing(services):
    @services.factory("foo")
    def foo_factory():
        return "I am foo"

    @annotate
    class Tic:
        foo: Any = attr("foo")

        def __init__(self, foo):
            self.foo = foo

        def __call__(self):
            return {"foo": self.foo}

    class Tac(Tic):
        ...

    result = await services.apply(Tac)

    assert result() == {"foo": "I am foo"}


@pytest.mark.asyncio
async def test_annotated_class_attribute(services):
    @services.factory("foo")
    def foo_factory():
        return "I am foo"

    @annotate
    class Tic:
        foo: Any = attr("foo")

        def __call__(self):
            return {"foo": self.foo}

    result = await services.apply(Tic)

    assert result() == {"foo": "I am foo"}


@pytest.mark.asyncio
async def test_annotated_class_attribute_2(services):
    """With an __init__
    """

    @services.factory("foo")
    def foo_factory():
        return "I am foo"

    @annotate
    class Tic:
        bar: Any = attr("foo")

        def __init__(self, foo, bar):
            self.foo = foo
            self.bar = bar

        def __call__(self):
            return {"foo": self.foo, "bar": self.bar}

    result = await services.apply(Tic, "value")

    assert result() == {"foo": "value", "bar": "I am foo"}

import pytest

from knighted import Injector, attr, attr_lazy
from typing import Any


@pytest.fixture
def services():
    class MyInjector(Injector):
        pass

    return MyInjector()


@pytest.mark.asyncio
async def test_descriptor_1_decorated(services):
    @services.factory("foo")
    async def foo_factory():
        return "I am foo"

    class Toto:
        cache: Any = attr("foo")

    toto = Toto
    with services.auto(), pytest.raises(Exception):
        await toto.cache


@pytest.mark.asyncio
async def test_descriptor_2_decorated(services):
    @services.factory("foo")
    async def foo_factory():
        return "I am foo"

    class Toto:
        cache: Any = attr_lazy("foo")

    toto = Toto()
    with services.auto():
        cache = await toto.cache
    assert cache == "I am foo"


@pytest.mark.asyncio
async def test_annotated_class_attribute(services):
    @services.factory("foo")
    def foo_factory():
        return "I am foo"

    class Tic:
        foo: Any = attr_lazy("foo")

        async def __call__(self):
            return {"foo": await self.foo}

    result = await services.apply(Tic)

    assert (await result()) == {"foo": "I am foo"}

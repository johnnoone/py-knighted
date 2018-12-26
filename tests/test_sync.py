import pytest

from knighted import Injector, annotate, current_injector, attr


@pytest.fixture
def services():
    class MyInjector(Injector):
        pass

    return MyInjector()


@pytest.mark.asyncio
async def test_sync_async(services):
    @services.factory("foo")
    def foo_factory():
        return "I am foo"

    @annotate("foo")
    async def fun(foo):
        return {"foo": foo}

    assert await services.apply(fun) == {"foo": "I am foo"}


@pytest.mark.asyncio
async def test_sync_sync(services):
    @services.factory("foo")
    def foo_factory():
        return "I am foo"

    @annotate("foo")
    def fun(foo):
        return {"foo": foo}

    assert await services.apply(fun) == {"foo": "I am foo"}


@pytest.mark.asyncio
async def test_async_async(services):
    @services.factory("foo")
    async def foo_factory():
        return "I am foo"

    @annotate("foo")
    async def fun(foo):
        return {"foo": foo}

    assert await services.apply(fun) == {"foo": "I am foo"}


@pytest.mark.asyncio
async def test_auto_sync_async(services):
    @services.factory("foo")
    def foo_factory():
        return "I am foo"

    @annotate("foo")
    async def fun(foo):
        return {"foo": foo}

    result = await services.apply(fun)

    assert result == {"foo": "I am foo"}


@pytest.mark.asyncio
async def test_auto_async_async(services):
    @services.factory("foo")
    async def foo_factory():
        return "I am foo"

    @services.factory("bar")
    async def bar_factory():
        return "I am bar"

    @annotate("bar")
    async def fun1(bar):
        return bar

    @annotate("foo")
    async def fun(foo):
        bar = await current_injector().apply(fun1)
        return {"foo": foo, "bar": bar}

    result = await services.apply(fun)

    assert result == {"foo": "I am foo", "bar": "I am bar"}


@pytest.mark.asyncio
async def test_noauto_partial_async_async(services):
    @services.factory("foo")
    async def foo_factory():
        return "I am foo"

    @services.factory("bar")
    async def bar_factory():
        return "I am bar"

    @annotate("bar")
    async def fun1(bar):
        return bar

    @annotate("foo")
    async def fun(foo):
        bar = await current_injector().apply(fun1)
        return {"foo": foo, "bar": bar}

    with pytest.raises(TypeError):
        await fun()


@pytest.mark.asyncio
async def test_descriptor_1_decorated(services):
    @services.factory("foo")
    async def foo_factory():
        return "I am foo"

    class Toto:
        cache = attr("foo")

    toto = Toto
    with services.auto(), pytest.raises(Exception):
        await toto.cache


@pytest.mark.asyncio
async def test_descriptor_2_decorated(services):
    @services.factory("foo")
    async def foo_factory():
        return "I am foo"

    class Toto:
        cache = attr("foo")

    toto = Toto()
    with services.auto():
        cache = await toto.cache
    assert cache == "I am foo"


@pytest.mark.asyncio
async def test_descriptor_1_not_decorated(services):
    @services.factory("foo")
    async def foo_factory():
        return "I am foo"

    class Toto:
        cache = attr("foo")

    toto = Toto
    with pytest.raises(Exception):
        toto.cache  # Must fails


@pytest.mark.asyncio
async def test_descriptor_2_not_decorated(services):
    @services.factory("foo")
    async def foo_factory():
        return "I am foo"

    class Toto:
        cache = attr("foo")

    toto = Toto()
    with pytest.raises(LookupError):
        toto.cache


@pytest.mark.asyncio
async def test_partial_sync_async(services):
    @services.factory("foo")
    def foo_factory():
        return "I am foo"

    @annotate("foo")
    async def fun(foo):
        return {"foo": foo}

    partial = services.partial(fun)
    assert await partial() == {"foo": "I am foo"}


@pytest.mark.asyncio
async def test_partial_outsider(services):
    async def fun():
        return {"foo": "bar"}

    partial = services.partial(fun)
    assert await partial() == {"foo": "bar"}

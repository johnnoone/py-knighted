import pytest
from knighted import Injector, annotate, current_injector
import asyncio
from contextlib import contextmanager
from time import time_ns, sleep


@pytest.fixture
def services():
    class MyInjector(Injector):
        pass

    return MyInjector()


class Timer:
    started_at = None
    stoped_at = None
    duration = None


@contextmanager
def timed():
    timer = Timer()
    timer.started_at = time_ns()
    yield timer
    timer.stoped_at = time_ns()
    timer.duration = timer.stoped_at - timer.started_at


@pytest.mark.asyncio
async def test_instance_factory(services):
    print("caca")

    @services.factory("foo")
    def foo_factory():
        return "I am foo"

    @services.factory("bar")
    async def bar_factory():
        return "I am bar"

    @services.factory("all")
    async def together_factory():
        foo = await services.get("foo")
        bar = await services.get("bar")
        return [foo, bar]

    @annotate("foo", "bar")
    def fun(foo, bar):
        return {"foo": foo, "bar": bar}

    @annotate("foo", "bar")
    async def awaitable_fun(foo, bar):
        return {"foo": foo, "bar": bar}

    assert (await services.get("foo")) == "I am foo"
    assert (await services.get("bar")) == "I am bar"
    assert (await services.get("all")) == ["I am foo", "I am bar"]
    # synchroneous
    assert (await services.apply(fun)) == {"foo": "I am foo", "bar": "I am bar"}
    # asynchroneous
    assert (await services.apply(awaitable_fun)) == {
        "foo": "I am foo",
        "bar": "I am bar",
    }


@pytest.mark.asyncio
async def test_fill_the_gaps(services):
    @services.factory("foo:1")
    def foo_factory():
        return "I am foo"

    @services.factory("bar:2")
    async def bar_factory():
        return "I am bar"

    @services.factory("all")
    async def together_factory():
        foo = await services.get("foo:1")
        bar = await services.get("bar:2")
        return [foo, bar]

    @annotate("foo:1", "bar:2")
    def fun(foo, bar):
        return {"foo": foo, "bar": bar}

    assert (await services.get("foo:1")) == "I am foo"
    assert (await services.get("bar:2")) == "I am bar"
    assert (await services.apply(fun)) == {"foo": "I am foo", "bar": "I am bar"}
    assert (await services.apply(fun, "obviously")) == {
        "foo": "obviously",
        "bar": "I am bar",
    }
    assert (await services.apply(fun, "obviously", "not")) == {
        "foo": "obviously",
        "bar": "not",
    }
    assert (await services.apply(fun, foo="sometimes")) == {
        "foo": "sometimes",
        "bar": "I am bar",
    }
    assert (await services.apply(fun, bar="I feel")) == {
        "foo": "I am foo",
        "bar": "I feel",
    }


@pytest.mark.slow
@pytest.mark.asyncio
async def test_load_in_parallel(services):
    @services.factory("foo")
    def foo_factory():
        sleep(1)
        return "I am foo"

    @services.factory("bar")
    async def bar_factory():
        await asyncio.sleep(1)
        return "I am bar"

    @services.factory("baz")
    async def baz_factory():
        await asyncio.sleep(1)
        return "I am baz"

    @annotate("foo", "bar", "baz")
    def fun(foo, bar, baz):
        return {"foo": foo, "bar": bar, "baz": baz}

    with timed() as timer:
        await services.apply(fun)
    assert timer.duration == pytest.approx(1000000000, rel=1e-2)


@pytest.mark.asyncio
async def test_class_factory():
    class MyInjector(Injector):
        pass

    @MyInjector.factory("foo")
    def foo_factory():
        return "I am foo"

    @MyInjector.factory("bar")
    def bar_factory():
        return "I am bar"

    @MyInjector.factory("all")
    async def together_factory():
        foo = await services.get("foo")
        bar = await services.get("bar")
        return [foo, bar]

    @annotate("foo", "bar")
    def fun(foo, bar):
        return {"foo": foo, "bar": bar}

    services = MyInjector()

    assert (await services.get("foo")) == "I am foo"
    assert (await services.get("bar")) == "I am bar"
    assert (await services.get("all")) == ["I am foo", "I am bar"]
    assert (await services.apply(fun)) == {"foo": "I am foo", "bar": "I am bar"}


@pytest.mark.asyncio
async def test_undefined_service_error(services):

    with pytest.raises(ValueError):
        await services.get("foo")


def test_annotate_error():
    for val in (True, False, None, []):
        with pytest.raises(ValueError):
            annotate(val)


@pytest.mark.asyncio
async def test_kw_apply(services):
    @services.factory("bar")
    def factory_bar():
        return "I am bar"

    @annotate(foo="bar")
    def fun(foo, *, bar):
        return "%s, not %s" % (foo, bar)

    def fun2(baz):
        return "nor %s" % baz

    assert (await services.apply(fun, bar="baz")) == "I am bar, not baz"
    assert (await services.apply(fun2, "baz")) == "nor baz"


@pytest.mark.asyncio
async def test_late_register(services):
    def factory_foo():
        return "I am foo"

    services.factory("foo", factory_foo)

    assert (await services.get("foo")) == "I am foo"


@pytest.mark.asyncio
async def test_sub_factory(services):
    @services.factory("foo")
    def foo_factory():
        return "I am foo"

    @services.factory("foo:bar")
    def bar_factory():
        return "I am bar"

    assert (await services.get("foo")) == "I am foo"
    assert (await services.get("foo:bar")) == "I am bar"


@pytest.mark.asyncio
async def test_close(services):
    @services.factory("foo")
    def foo_factory():
        return "I am foo"

    @services.factory("foo:bar")
    def bar_factory():
        return "I am bar"

    assert len(services.services) == 0
    await services.get("foo")
    await services.get("foo:bar")
    assert len(services.services) == 2
    services.close()
    assert len(services.services) == 0


def test_close_register(services):
    class Foo:
        def __init__(self):
            self.value = "bar"

        def set_value(self, value):
            self.value = value

    foo = Foo()

    def reaction(obj):
        obj.set_value("baz")

    services.close.register(foo, reaction=reaction)
    services.close()
    assert foo.value == "baz"


def test_close_unregister(services):
    class Foo:
        def __init__(self):
            self.value = "bar"

        def set_value(self, value):
            self.value = value

    foo = Foo()

    def reaction(obj):
        obj.set_value("baz")

    services.close.register(foo, reaction=reaction)
    services.close.unregister(foo, reaction=reaction)
    services.close()
    assert foo.value == "bar"


@pytest.mark.asyncio
async def test_singleton(services):
    @services.factory("foo")
    def foo_factory():
        return time_ns()

    result1 = await services.get("foo")
    sleep(0.1)
    result2 = await services.get("foo")
    assert result1 == result2

    # forget will make forget foo
    services.refresh("foo")
    result3 = await services.get("foo")
    assert result1 != result3


@pytest.mark.asyncio
async def test_not_singleton(services):
    @services.factory("foo", singleton=False)
    def foo_factory():
        return time_ns()

    result1 = await services.get("foo")
    sleep(0.1)
    result2 = await services.get("foo")
    assert result1 != result2


@pytest.mark.asyncio
async def test_service_context(services):
    def func():
        return current_injector()

    assert func() is None
    assert (await services.apply(func)) is services

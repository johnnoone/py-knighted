import pytest
from knighted import Injector, annotate


@pytest.mark.asyncio
async def test_instance_factory():
    class MyInjector(Injector):
        pass

    services = MyInjector()

    @services.factory('foo')
    def foo_factory():
        return 'I am foo'

    @services.factory('bar')
    async def bar_factory():
        return 'I am bar'

    @services.factory('all')
    async def together_factory():
        foo = await services.get('foo')
        bar = await services.get('bar')
        return [foo, bar]

    @annotate('foo', 'bar')
    def fun(foo, bar):
        return {'foo': foo,
                'bar': bar}

    @annotate('foo', 'bar')
    async def awaitable_fun(foo, bar):
        return {'foo': foo,
                'bar': bar}

    assert (await services.get('foo')) == 'I am foo'
    assert (await services.get('bar')) == 'I am bar'
    assert (await services.get('all')) == ['I am foo', 'I am bar']
    assert (await services.apply(fun)) == {'foo': 'I am foo',
                                           'bar': 'I am bar'}
    assert (await services.apply(awaitable_fun)) == {'foo': 'I am foo',
                                                     'bar': 'I am bar'}


@pytest.mark.asyncio
async def test_partial():
    class MyInjector(Injector):
        pass

    services = MyInjector()

    @services.factory('foo')
    def foo_factory():
        return 'I am foo'

    @services.factory('bar')
    def bar_factory():
        return 'I am bar'

    @annotate('foo', 'bar')
    def fun(foo, bar):
        return {'foo': foo,
                'bar': bar}

    assert len(services.services) == 0
    part = services.partial(fun)
    assert len(services.services) == 0
    assert (await part()) == {'foo': 'I am foo', 'bar': 'I am bar'}
    assert len(services.services) == 2


@pytest.mark.asyncio
async def test_class_factory():
    class MyInjector(Injector):
        pass

    @MyInjector.factory('foo')
    def foo_factory():
        return 'I am foo'

    @MyInjector.factory('bar')
    def bar_factory():
        return 'I am bar'

    @MyInjector.factory('all')
    async def together_factory():
        foo = await services.get('foo')
        bar = await services.get('bar')
        return [foo, bar]

    @annotate('foo', 'bar')
    def fun(foo, bar):
        return {'foo': foo,
                'bar': bar}

    services = MyInjector()

    assert (await services.get('foo')) == 'I am foo'
    assert (await services.get('bar')) == 'I am bar'
    assert (await services.get('all')) == ['I am foo', 'I am bar']
    assert (await services.apply(fun)) == {'foo': 'I am foo',
                                           'bar': 'I am bar'}


@pytest.mark.asyncio
async def test_undefined_service_error():
    class MyInjector(Injector):
        pass

    services = MyInjector()

    with pytest.raises(ValueError):
        await services.get('foo')


def test_annotate_error():
    for val in (True, False, None, []):
        with pytest.raises(ValueError):
            annotate(val)


@pytest.mark.asyncio
async def test_kw_apply():
    class MyInjector(Injector):
        pass

    services = MyInjector()

    @services.factory('bar')
    def factory_bar():
        return 'I am bar'

    @annotate(foo='bar')
    def fun(foo, *, bar):
        return '%s, not %s' % (foo, bar)

    def fun2(baz):
        return 'nor %s' % baz

    assert (await services.apply(fun, bar='baz')) == 'I am bar, not baz'
    assert (await services.apply(fun2, 'baz')) == 'nor baz'


@pytest.mark.asyncio
async def test_late_register():
    class MyInjector(Injector):
        pass

    def factory_foo():
        return 'I am foo'

    services = MyInjector()
    services.factory('foo', factory_foo)

    assert (await services.get('foo')) == 'I am foo'


@pytest.mark.asyncio
async def test_sub_factory():
    class MyInjector(Injector):
        pass

    services = MyInjector()

    @services.factory('foo')
    def foo_factory():
        return 'I am foo'

    @services.factory('foo:bar')
    def bar_factory():
        return 'I am bar'

    assert (await services.get('foo')) == 'I am foo'
    assert (await services.get('foo:bar')) == 'I am bar'


@pytest.mark.asyncio
async def test_close():
    class MyInjector(Injector):
        pass

    services = MyInjector()

    @services.factory('foo')
    def foo_factory():
        return 'I am foo'

    @services.factory('foo:bar')
    def bar_factory():
        return 'I am bar'

    assert len(services.services) == 0
    await services.get('foo')
    await services.get('foo:bar')
    assert len(services.services) == 2
    services.close()
    assert len(services.services) == 0


def test_close_register():
    class MyInjector(Injector):
        pass

    services = MyInjector()

    class Foo:

        def __init__(self):
            self.value = 'bar'

        def set_value(self, value):
            self.value = value

    foo = Foo()

    def reaction(obj):
        obj.set_value('baz')
    services.close.register(foo, reaction=reaction)
    services.close()
    assert foo.value == 'baz'


def test_close_unregister():
    class MyInjector(Injector):
        pass

    services = MyInjector()

    class Foo:

        def __init__(self):
            self.value = 'bar'

        def set_value(self, value):
            self.value = value

    foo = Foo()

    def reaction(obj):
        obj.set_value('baz')
    services.close.register(foo, reaction=reaction)
    services.close.unregister(foo, reaction=reaction)
    services.close()
    assert foo.value == 'bar'

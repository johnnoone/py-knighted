import pytest
from aiocompose import Injector, annotate


@pytest.mark.asyncio
def test_instance_factory():
    class MyInjector(Injector):
        pass

    services = MyInjector()

    @services.factory('foo')
    def foo_factory():
        return 'I am foo'

    @services.factory('bar')
    def bar_factory():
        return 'I am bar'

    @services.factory('all')
    def together_factory():
        foo = yield from services.get('foo')
        bar = yield from services.get('bar')
        return [foo, bar]

    @annotate('foo', 'bar')
    def fun(foo, bar):
        return {'foo': foo,
                'bar': bar}

    assert (yield from services.get('foo')) == 'I am foo'
    assert (yield from services.get('bar')) == 'I am bar'
    assert (yield from services.get('all')) == ['I am foo', 'I am bar']
    assert (yield from services.inject(fun)) == {'foo': 'I am foo',
                                                 'bar': 'I am bar'}


@pytest.mark.asyncio
def test_class_factory():
    class MyInjector(Injector):
        pass

    @MyInjector.factory('foo')
    def foo_factory():
        return 'I am foo'

    @MyInjector.factory('bar')
    def bar_factory():
        return 'I am bar'

    @MyInjector.factory('all')
    def together_factory():
        foo = yield from services.get('foo')
        bar = yield from services.get('bar')
        return [foo, bar]

    @annotate('foo', 'bar')
    def fun(foo, bar):
        return {'foo': foo,
                'bar': bar}

    services = MyInjector()

    assert (yield from services.get('foo')) == 'I am foo'
    assert (yield from services.get('bar')) == 'I am bar'
    assert (yield from services.get('all')) == ['I am foo', 'I am bar']
    assert (yield from services.inject(fun)) == {'foo': 'I am foo',
                                                 'bar': 'I am bar'}


@pytest.mark.asyncio
def test_undefined_service_error():
    class MyInjector(Injector):
        pass

    services = MyInjector()

    with pytest.raises(ValueError):
        yield from services.get('foo')


def test_annotate_error():
    for val in (True, False, None, []):
        with pytest.raises(ValueError):
            annotate(val)


@pytest.mark.asyncio
def test_kw_inject():
    class MyInjector(Injector):
        pass

    services = MyInjector()

    @services.factory('bar')
    def factory_bar():
        return 'I am bar'

    @annotate(foo='bar')
    def fun(foo, *, bar):
        return '%s, not %s' % (foo, bar)

    assert (yield from services.inject(fun, bar='baz')) == 'I am bar, not baz'


@pytest.mark.asyncio
def test_late_register():
    class MyInjector(Injector):
        pass

    def factory_foo():
        return 'I am foo'

    services = MyInjector()
    services.factory('foo', factory_foo)

    assert (yield from services.get('foo')) == 'I am foo'


@pytest.mark.asyncio
def test_sub_factory():
    class MyInjector(Injector):
        pass

    services = MyInjector()

    @services.factory('foo')
    def foo_factory():
        return 'I am foo'

    @services.factory('foo:bar')
    def bar_factory():
        return 'I am bar'

    assert (yield from services.get('foo')) == 'I am foo'
    assert (yield from services.get('foo:bar')) == 'I am bar'

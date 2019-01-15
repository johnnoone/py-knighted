Knighted
========


Knighted, is heavily inspired by jeni_ and works only with asyncio_.
It allows to described dependencies, and inject them later.

For example::

    from knighted import annotation, Injector

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

    assert (yield from services.apply(fun)) == {'foo': 'I am foo',
                                                'bar': 'I am bar'}


The `func()` can be a function or an awaitable. These 2 examples works the same::


    @annotate('foo', 'bar')
    def sync_fun(foo, bar):
        return {'foo': foo,
                'bar': bar}

    assert (yield from services.apply(sync_fun)) == {'foo': 'I am foo',
                                                     'bar': 'I am bar'}


    @annotate('foo', 'bar')
    async def awaitable_fun(foo, bar):
        return {'foo': foo,
                'bar': bar}

    assert (yield from services.apply(awaitable_fun)) == {'foo': 'I am foo',
                                                          'bar': 'I am bar'}


When applied with some arguments, placeholders just fills the gaps::


    @annotate('foo', 'bar')
    def fun(foo, bar):
        return {'foo': foo,
                'bar': bar}

    assert (yield from services.apply(fun, foo="yes")) == {'foo': 'yes',
                                                           'bar': 'I am bar'}


    @annotate('foo', 'bar')
    async def awaitable_fun(foo, bar):
        return {'foo': foo,
                'bar': bar}

    assert (yield from services.apply(awaitable_fun)) == {'foo': 'I am foo',
                                                          'bar': 'I am bar'}


Factories also can be either sync or awaitable::

    @services.factory('bar:sync')
    def bar_factory():
        return 'I am bar'

    @services.factory('bar:awaitable')
    async def bar_factory():
        return 'I am bar'


Services are by default singleton, but they can also be instantiated at every call::

    @services.factory('bar', singleton=True)
    def bar_factory():
        return time()

    result1 = await services.get('bar')
    sleep(.1)
    result2 = await services.get('bar')
    assert result1 == result2

    # cache can be resetted

    services.refresh("bar")
    result3 = await services.get('bar')
    assert result3 != result2


Singleton mode can be disabled per service::

    @services.factory('baz', singleton=False)
    def baz_factory():
        return time()

    result1 = await services.get('baz')
    sleep(.1)
    result2 = await services.get('baz')
    assert result1 != result2


Current services are automatically exposed inside functions::

    def func():
        return current_injector()

    assert func() is None
    assert (await services.apply(func)) is services



Implementation
--------------

``annotate(*args, **kwargs)`` annotate a func with service names.

``coroutine Injector.factory(name)`` declare a service factory

``coroutine Injector.get(name)`` return the service instance

``coroutine Injector.apply(func, *args, **kwargs)`` call the annoted callable
with the mounted service.

``coroutine Injector.partial(func)`` prepare an annoted func with later services.

``coroutine Injector.close()`` clear all cached services., and call all deferred
close().

``coroutine Injector.close.register(obj)`` defers ``yield from obj.close()`` when
``Injector.close()`` is called.


Factories don't need to be fully qualified. For example::

    @services.factory('prefix')
    def foo_factory(bar):
        return 'I am foo and ' + bar

    assert (yield from services.get('prefix:baz')) == 'I am foo and baz'
    assert (yield from services.get('prefix:qux')) == 'I am foo and qux'


Closing callback can be registered::

    class Foo:
        def close(self):
            self.closed = True
    foo = Foo()
    services.close.register(foo)
    services.close()
    assert foo.closed == True


Annotated functions can be rendered partially::

    @annotate('foo', 'bar')
    def fun(foo, bar):
        return {'foo': foo,
                'bar': bar}

    partial = services.partial(fun)
    assert (yield from partial()) == {'foo': 'I am foo',
                                      'bar': 'I am bar'}


Injector has a mapping interface, which allows to register arbitrary values::

    services["foo"] = "yes"
    assert await services["foo"] == "yes"


Injection works for class too. Injector is already dataclass ready.
These 3 examples are equivalent and performs the same::

    from dataclasses import dataclass, field
    from knighted import attr, annotate, KNIGHTED_NAMESPACE

    @annotate
    class Foo:
        my_attr = attr("foo")

    @dataclass
    class Bar:
        my_attr = attr("foo")

    @dataclass
    class Baz:
        my_attr: Any = field(namespace={KNIGHTED_NAMESPACE:"foo"})

the my_attr will be resolved like the function way.



.. _asyncio: https://pypi.python.org/pypi/asyncio
.. _jeni: https://pypi.python.org/pypi/jeni

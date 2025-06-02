```pip install build twine

python -m build
```

Publish to TestPyPI (RECOMMENDED FIRST)

Register at [TestPyPI](https://test.pypi.org/).

```
python -m twine upload --repository testpypi dist/*
```

If all is good, try installing your package from testpypi in a new virtualenv:
```
pip install --index-url https://test.pypi.org/simple/ factverifai

```

Publish to RealPyPI
```
python -m twine upload dist/*
```
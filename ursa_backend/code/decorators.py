from pathlib import Path


def saver(obj, path: Path):
    return 1


def loader(path: Path):
    return 1


def cache(path: Path):
    def _decorator(func):
        def _wrapper(*args, **kwargs):
            if path.exists():
                result = loader(path)
            else:
                result = func(*args, **kwargs)
                saver(result, path)
            return result

        return _wrapper

    return _decorator


def cache_nonsave(path: Path):
    def _decorator(function):
        def _wrapper(*args, **kwargs):
            if not path.exists():
                function(*args, **kwargs)
            return None

        return _wrapper

    return _decorator

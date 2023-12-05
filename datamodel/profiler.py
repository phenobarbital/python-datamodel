import cProfile
import functools
import pstats


def profile(func):

    @functools.wraps(func)
    def inner(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        try:
            retval = func(*args, **kwargs)
        finally:
            profiler.disable()
            with open('profile.out', 'w') as profile_file:
                stats = pstats.Stats(profiler, stream=profile_file)
                stats.print_stats()
        return retval

    return inner

import cProfile
import scload
import pstats

cProfile.run('scload.scload()', 'prof.out')
p = pstats.Stats('prof.out')
p.strip_dirs().sort_stats('time').print_stats(50)

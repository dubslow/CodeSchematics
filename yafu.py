#! /usr/bin/env python3

from codeschematics.parsers.c_parser import CTraverser
from codeschematics.parsers.fake_libc_include import find_fake_libc_include
from codeschematics.presentation import Presenter
from pycparser import c_ast, c_parser, preprocess_file, parse_file

from sys import argv
from os.path import basename, join

################################################################################

main_dir = '/home/bill/yafu/dev/'
# besides yafu/include/ and yafu/factor/qs/, we also need GMP and zlib headers
includes = [join(main_dir, 'include/'), join(main_dir, 'factor/qs/'), '/usr/local/include/', '/usr/include/']

# print-%  : ; @echo $* = $($*)
# $ make print-YAFU_SRCS
# $ make print-YAFU_NFS_SRCS
# $ make print-MSIEVE_SRCS
files = "top/driver.c top/utils.c top/stack.c top/calc.c top/test.c top/mpz_prp_prime.c factor/factor_common.c factor/rho.c factor/squfof.c factor/trialdiv.c factor/tune.c factor/qs/filter.c factor/qs/tdiv.c factor/qs/tdiv_small.c factor/qs/tdiv_large.c factor/qs/tdiv_scan.c factor/qs/large_sieve.c factor/qs/new_poly.c factor/qs/siqs_test.c factor/tinyqs/tinySIQS.c factor/qs/siqs_aux.c factor/qs/smallmpqs.c factor/qs/SIQS.c factor/gmp-ecm/ecm.c factor/gmp-ecm/pp1.c factor/gmp-ecm/pm1.c factor/nfs/nfs.c arith/arith0.c arith/arith1.c arith/arith2.c arith/arith3.c top/eratosthenes/count.c top/eratosthenes/offsets.c top/eratosthenes/primes.c top/eratosthenes/roots.c top/eratosthenes/linesieve.c top/eratosthenes/soe.c top/eratosthenes/tiny.c top/eratosthenes/worker.c top/eratosthenes/soe_util.c top/eratosthenes/wrapper.c factor/qs/tdiv_med_32k.c factor/qs/tdiv_med_64k.c factor/qs/tdiv_resieve_32k.c factor/qs/tdiv_resieve_64k.c factor/qs/med_sieve_32k.c factor/qs/med_sieve_64k.c factor/qs/poly_roots_32k.c factor/qs/poly_roots_64k.c factor/qs/update_poly_roots_32k.c factor/qs/update_poly_roots_64k.c factor/nfs/nfs_sieving.c factor/nfs/nfs_poly.c factor/nfs/nfs_postproc.c factor/nfs/nfs_filemanip.c factor/nfs/nfs_threading.c factor/nfs/snfs.c factor/qs/msieve/lanczos.c factor/qs/msieve/lanczos_matmul0.c factor/qs/msieve/lanczos_matmul1.c factor/qs/msieve/lanczos_matmul2.c factor/qs/msieve/lanczos_pre.c factor/qs/msieve/sqrt.c factor/qs/msieve/savefile.c factor/qs/msieve/gf2.c"

files = [join(main_dir, f) for f in files.split()]

#dname = find_fake_libc_include()
#if dname:
#     cpp_args += ['-nostdinc', "-I{}".format(dname)]
#text = preprocess_file(filepath, cpp_args=cpp_args)

#dic, nested = make_call_dict(filepath, include_dirs=includes) # Ignore the nested funcs retval

cpp_args = []
dname = find_fake_libc_include()
cpp_args += ['-nostdinc', "-I{}".format(dname)]
cpp_args += ["-I{}".format(idir) for idir in includes]
cpp_args += ['-D__attribute__(x)=', '-D__inline__=', '-D__inline=', '-Dvolatile=', '-D__asm__(x,y)=']
from subprocess import Popen, PIPE

ast = parse_file(files[0], use_cpp=True, cpp_args=cpp_args)

for f in files[1:]:
     path_list = ['cpp'] + cpp_args + [f]
     print(' '.join(path_list))
     pipe = Popen(path_list, stdout=PIPE, universal_newlines=True)
     text = pipe.communicate()[0]
     with open('tmpyafu.c', 'w') as fasdf:
          fasdf.write(text)
     ast.ext += parse_file(f, use_cpp=True, cpp_args=cpp_args).ext

visitor = CTraverser()
visitor.visit(ast)

tree = Presenter(visitor.result())

fname = 'libyafu'
tree = tree.default_filter()
tree.to_svg(fname)

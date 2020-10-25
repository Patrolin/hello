#!/usr/bin/env python3
import subprocess, shutil, os, re
from subprocess import run
from time import perf_counter_ns
from math import *
import itertools

def walk(cmds: any, prefix=''):
	if isinstance(cmds, str):
		yield cmds
	elif isinstance(cmds, dict):
		for (key, value) in cmds.items():
			for subvalue in walk(value):
				yield f'{key}{subvalue}'
	elif isinstance(cmds, list):
		for value in cmds:
			for subvalue in walk(value):
				yield subvalue
	elif isinstance(cmds, tuple):
		for value in walk(cmds[0]):
			if len(cmds) > 1:
				for subvalue in walk(cmds[1:]):
					yield f'{value}{subvalue}'
			else:
				yield value
	else:
		raise TypeError('cmds must be of type str|dict|list|tuple')

def measure(result: list, cmd: str, path: str):
	print(cmd)
	try:
		os.remove(path)
	except FileNotFoundError:
		pass
	try:
		os.remove(f'{path}.o')
	except FileNotFoundError:
		pass
	build_start = perf_counter_ns()
	run(cmd, shell=True, check=True)
	build_end = perf_counter_ns()
	run_times = []
	for i in range(100):
		run_start = perf_counter_ns()
		if run(path, stdout=subprocess.PIPE, check=True, encoding='utf-8').stdout != 'hello world\n':
			raise ValueError('process did not return "hello world\\n"')
		run_end = perf_counter_ns()
		run_times.append(run_end - run_start)
	stat = run(['stat', path], stdout=subprocess.PIPE, encoding='utf-8')
	file_size = int(re.search(r'Size: *(\d+)', stat.stdout, re.M)[1])
	size = run(['size', '-A', path], stdout=subprocess.PIPE, encoding='utf-8')
	obj_size = int(re.search(r'Total *(\d+)', size.stdout, re.M)[1])
	result.append({
		'cmd': cmd,
		'file_size': file_size,
		'obj_size': obj_size,
		'elf_size': (file_size - obj_size),
		'build_time': (build_end - build_start),
		'run_time': min(run_times),
	})

if __name__ == '__main__':
	path = './hello'
	result = []
	C_ARGS = (f' {path}.c -o {path}', ['', ' -O1', ' -O2', ' -O3'], ['', ' -static'], ['', ' -s'])
	for cmd in walk(({
		'clang': C_ARGS,
		'gcc': C_ARGS,
		'nasm': (f' -f elf64 {path}.S', [f' && gcc {path}.o -o {path} -static -nostartfiles -nostdlib -nodefaultlibs', f' && ld {path}.o -o {path}']),
		'zig': (f' build-exe {path}.zig', ['', ' --release-safe', ' --release-fast', ' --release-small'], ['', ' --strip']),
	}, ['', f' && strip {path}'])):
		measure(result, cmd, path)
	os.remove(path)
	os.remove(f'{path}.o')
	for (result_path, sort_key, group_key) in (
		('by_size.txt', lambda x: (x['file_size'], x['elf_size'], round(x['run_time'] / 1e5) / 10, round(log2(x['build_time'] / 1e6)), x['cmd']), lambda x: round(log2(x['file_size']))),
		('by_build_time.txt', lambda x: (round(log2(x['build_time'] / 1e6)), x['file_size'], x['elf_size'], round(x['run_time'] / 1e5) / 10, x['cmd']), lambda x: round(log2(x['build_time'] / 1e6))),
		('by_run_time.txt', lambda x: (round(x['run_time'] / 1e5) / 10, x['file_size'], x['elf_size'], round(log2(x['build_time'] / 1e6)), x['cmd']), lambda x: round(log2(x['run_time'] / 1e6))),
	):
		sorted_result = sorted(result, key=sort_key)
		grouped_result = [list(A) for count, A in itertools.groupby(sorted_result, key=group_key)]
		with open(result_path, 'w+') as f:
			f.write(f'{"Elf size": <8}   {"Obj size": <9}   {"Build time": <10}   {"Run time": <8}   {"Command"}\n')
			for group in grouped_result:
				for row in group:
					cmd, file_size, obj_size, elf_size, build_time, run_time = row.values()
					f.write(
					    f'{elf_size: >8,} + {obj_size: >7,} B   {2 ** round(log2(build_time / 1e6)): >7} ms   {round(run_time / 1e5) / 10: >5} ms   {cmd}\n'
					)
				f.write('\n')

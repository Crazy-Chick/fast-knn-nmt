# encoding: utf-8
"""



build faiss indexes for DataStores extracted by build_ds.py
"""

import argparse
import os
from multiprocessing import Pool
import re

from tqdm import tqdm

from fast_knn_nmt.knn.index_builder import IndexBuilder
from fast_knn_nmt.utils.logger import get_logger


LOGGING = get_logger(__name__)


def main():
    """main"""
    parser = argparse.ArgumentParser(description='build faiss indexes')
    parser.add_argument("--dstore-dir", type=str, required=True, help="paths to data store. if provided multiple,"
                                                                      "use ',' as separator")
    parser.add_argument("--subdirs", action="store_true",
                        help="if True, each subdir of dstore_dir is a candidate dstore dir.")
    parser.add_argument("--subdirs-range", type=str, default="",
                        help="if set, only build knn for directory name like token_start, token_end. "
                             "where token_start, token_end = subdirs_range.split(',')")
    parser.add_argument("--overwrite", action="store_true",
                        help="if True, delete old faiss_store files before generating new ones")
    parser.add_argument("--index-type", type=str, default="auto",
                        help="faiss index type"),
    parser.add_argument('--seed', type=int, default=0, help='random seed')
    parser.add_argument('--chunk-size', default=1000000, type=int,
                        help='can only load a certain amount of data to memory at a time.')
    parser.add_argument('--use-gpu', default=False, action='store_true',
                        help='if true, use gpu for training')
    parser.add_argument('--workers', type=int, default=1, help='number of cpu')
    parser.add_argument('--metric', type=str, default="l2", choices=["l2", "ip", "cosine"],
                        help='faiss index metric, l2 for L2 distance, ip for inner product, '
                             'cosine for cosine similarity')
    parser.add_argument("--use-cluster", action="store_true",
                        help="if True, use k-means")
    args = parser.parse_args()
    if not args.subdirs:
        all_dirs = [d for d in args.dstore_dir.split(",") if d.strip()]
    else:
        parent_dirs = [d for d in args.dstore_dir.split(",") if d.strip()]
        all_dirs = []
        for parent_dir in parent_dirs:
            subdirs = os.listdir(args.dstore_dir)
            for subdir in subdirs:
                d = os.path.join(parent_dir, subdir)
                if os.path.isdir(d):
                    all_dirs.append(d)

    if args.subdirs_range:
        start, end = args.subdirs_range.split(",")
        start = int(start)
        end = int(end)
        valid_all_dirs = []
        for d in all_dirs:
            match_idx = re.match("token_(\d+)", os.path.basename(d))
            if match_idx is None:
                continue
            match_idx = int(match_idx.group(1))
            if start <= match_idx < end:
                valid_all_dirs.append(d)
        all_dirs = valid_all_dirs

    print(f"Select {len(all_dirs)} dir to build indexes")

    if args.workers > 1:
        pool = Pool(args.workers)
        results = []
        for dstore_dir in all_dirs:
            results.append(pool.apply_async(build, args=(dstore_dir, args)))
        pool.close()
        for r in tqdm(results):
            r.get()
    else:
        for dstore_dir in tqdm(all_dirs):
            print(dstore_dir)
            build(dstore_dir, args)


def build(dstore_dir, args):
    try:
        index_builder = IndexBuilder(dstore_dir=dstore_dir, use_gpu=args.use_gpu, metric=args.metric, use_cluster=args.use_cluster)

        if args.overwrite or not index_builder.exists():
            index_builder.build(index_type=args.index_type, seed=args.seed, chunk_size=args.chunk_size, overwrite=args.overwrite)
    except Exception as e:
        LOGGING.error(f"Error at building index for {dstore_dir}", exc_info=1)


if __name__ == '__main__':
    main()

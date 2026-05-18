#!/usr/bin/env python3

import itertools
import pathlib
import datetime
import logging

import config
import test_runner
import diffs

config.RESULTS_DIR.mkdir(exist_ok=True)
config.DIFFS_DIR.mkdir(exist_ok=True)
config.LOG_DIR.mkdir(exist_ok=True)

# Configuring the logger

# Adding the output stream to the file
file_log = logging.FileHandler(config.LOG_DIR / f"regress_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
# And output to the console
console_out = logging.StreamHandler()
# Specify these two streams in the logger settings
logging.basicConfig(handlers=(file_log, console_out), level=logging.DEBUG)

# Get the servers and all possible unique pairs of servers without repetition and without taking into account the order
servers = config.POSTGRES_SERVERS.keys()
pairs = list(itertools.combinations(servers, 2))

# Go in a loop through groups of two servers: a test is running simultaneously on both servers in a group,
# and therefore both servers are both remote and local with postgres_fdw at the same time
for s1, s2 in pairs:
    cfg_a = config.POSTGRES_SERVERS[s1]
    cfg_b = config.POSTGRES_SERVERS[s2]

    pair_name = f"{s1}_{s2}"
    logging.info(f"\n=== {pair_name} ===")

    res_dir = config.RESULTS_DIR / pair_name
    diff_dir = config.DIFFS_DIR / pair_name
    res_dir.mkdir(exist_ok=True)
    diff_dir.mkdir(exist_ok=True)

    # Run all the tests on the next pair of servers
    for test_name, test_cfg in config.TESTS.items():
        test_file = pathlib.Path(test_cfg["test_sql_script_path"])

        logging.info(f"Running: {test_name}")

        result_file_a = res_dir / f"{test_name}_{test_file.stem}_on_server_{s1}.out"
        result_file_b = res_dir / f"{test_name}_{test_file.stem}_on_server_{s2}.out"
        
        expected_file = pathlib.Path(test_cfg["test_expected_out_file_path"])

        # Running the test
        try:
            results_a, results_b = test_runner.run_test(test_cfg, cfg_a, cfg_b)
            
            result_file_a.write_text(results_a)
            result_file_b.write_text(results_b)

            diff_file_a = diff_dir / f"{test_name}_{test_file.stem}_on_server_{s1}.diff"
            diff_file_b = diff_dir / f"{test_name}_{test_file.stem}_on_server_{s2}.diff"

            # Generate diffs if there are differences in output between expected and received
            ok_a = diffs.create_diffs(result_file_a, expected_file, diff_file_a)
            ok_b = diffs.create_diffs(result_file_b, expected_file, diff_file_b)
            
            if ok_a and ok_b:
                logging.info(f"[PASS] {pair_name} | {test_name}")
            else:
                logging.info(f"[FAIL] {pair_name} | {test_name}")
                if not ok_a:
                    logging.info(f"       diff A: {diff_file_a}")
                if not ok_b:
                    logging.info(f"       diff B: {diff_file_b}")

        except Exception as e:
            logging.error(f"{pair_name} | {test_name}\n{str(e)}")
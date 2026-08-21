.PHONY: test eval-mocked eval-live eval-all benchmark

test:
	pytest eval/

eval-mocked:
	python eval/run_adk_eval_parallel.py --mode mocked -p 8

eval-live:
	python eval/run_adk_eval_parallel.py --mode live -p 8

eval-all: eval-mocked

benchmark: eval-mocked


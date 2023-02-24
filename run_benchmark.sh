#! /bin/bash
unset SPARK_HOME
SPARKCUML_HOME=`pwd`/src
export PYTHONPATH="$SPARKCUML_HOME:$PYTHONPATH"

### generate parquet dataset
python ./benchmark/gen_data.py \
    --num_rows 5000 \
    --num_cols 3000 \
    --dtype "float64" \
    --feature_type "array" \
    --output_dir "/tmp/5k_3k_float64.parquet" \
    --spark_conf "spark.master=local[*]" \
    --spark_confs "spark.driver.memory=128g" 


### local mode
CUDA_VISIBLE_DEVICES=0,1 python ./benchmark/bench_pca.py \
    --n_components 3 \
    --num_gpus 2 \
    --num_cpus 0 \
    --num_runs 3 \
    --parquet_path "/tmp/5k_3k_float64.parquet" \
    --report_path "./report.csv" \
    --spark_confs "spark.master=local[12]" \
    --spark_confs "spark.driver.memory=128g" \
    --spark_confs "spark.sql.execution.arrow.maxRecordsPerBatch=200000" 


### standalone mode
#SPARK_MASTER=spark://hostname:port
#tar -czvf sparkcuml.tar.gz -C ./src .
#
#python ./benchmark/bench_pca.py \
#    --n_components 3 \
#    --num_gpus 2 \
#    --num_cpus 0 \
#    --num_runs 3 \
#    --parquet_path "/tmp/5k_3k_float64.parquet" \
#    --report_path "./report_standalone.csv" \
#    --spark_confs "spark.master=${SPARK_MASTER}" \
#    --spark_confs "spark.driver.memory=128g" \
#    --spark_confs "spark.sql.execution.arrow.maxRecordsPerBatch=200000"  \
#    --spark_confs "spark.executor.memory=128g" \
#    --spark_confs "spark.rpc.message.maxSize=2000" \
#    --spark_confs "spark.pyspark.python=${PYTHON_ENV_PATH}" \
#    --spark_confs "spark.submit.pyFiles=./sparkcuml.tar.gz" \
#    --spark_confs "spark.task.resource.gpu.amount=1" \
#    --spark_confs "spark.executor.resource.gpu.amount=1" 
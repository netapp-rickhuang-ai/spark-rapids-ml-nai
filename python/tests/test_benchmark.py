import os
import sys

file_path = os.path.abspath(__file__)
file_dir_path = os.path.dirname(file_path)
extra_python_path = file_dir_path + "/../benchmark"
sys.path.append(extra_python_path)

from typing import List, Tuple

import numpy as np
import pandas as pd
import pytest
from pyspark.sql import DataFrame
from sklearn.datasets import make_blobs

from benchmark.bench_nearest_neighbors import CPUNearestNeighborsModel
from spark_rapids_ml.core import alias

from .sparksession import CleanSparkSession
from .utils import array_equal


def get_sgnn_res(
    X_item: np.ndarray, X_query: np.ndarray, n_neighbors: int
) -> Tuple[np.ndarray, np.ndarray]:
    from sklearn.neighbors import NearestNeighbors as SGNN

    sg_nn = SGNN(n_neighbors=n_neighbors)
    sg_nn.fit(X_item)
    sg_distances, sg_indices = sg_nn.kneighbors(X_query)
    return (sg_distances, sg_indices)


def assert_knn_equal(
    knn_df: DataFrame, id_col_name: str, distances: np.ndarray, indices: np.ndarray
) -> None:
    res_pd: pd.DataFrame = knn_df.sort(f"query_{id_col_name}").toPandas()
    mg_indices: np.ndarray = np.array(res_pd["indices"].to_list())
    mg_distances: np.ndarray = np.array(res_pd["distances"].to_list())

    assert array_equal(mg_indices, indices)
    assert array_equal(mg_distances, distances)


@pytest.mark.slow
def test_cpunn_withid() -> None:

    n_samples = 1000
    n_features = 50
    n_clusters = 10
    n_neighbors = 30

    X, _ = make_blobs(
        n_samples=n_samples,
        n_features=n_features,
        centers=n_clusters,
        random_state=0,
    )  # make_blobs creates a random dataset of isotropic gaussian blobs.

    sg_distances, sg_indices = get_sgnn_res(X, X, n_neighbors)

    with CleanSparkSession({}) as spark:

        def py_func(id: int) -> List[int]:
            return X[id].tolist()

        from pyspark.sql.functions import udf

        spark_func = udf(py_func, "array<float>")
        df = spark.range(len(X)).select("id", spark_func("id").alias("features"))

        mg_model = (
            CPUNearestNeighborsModel(df)
            .setInputCol("features")
            .setIdCol("id")
            .setK(n_neighbors)
        )

        _, _, knn_df = mg_model.kneighbors(df)
        assert_knn_equal(knn_df, "id", sg_distances, sg_indices)


# @pytest.mark.slow
def test_cpunn_noid() -> None:

    n_samples = 1000
    n_features = 50
    n_clusters = 10
    n_neighbors = 30

    X, _ = make_blobs(
        n_samples=n_samples,
        n_features=n_features,
        centers=n_clusters,
        random_state=0,
    )  # make_blobs creates a random dataset of isotropic gaussian blobs.

    with CleanSparkSession({}) as spark:

        df = spark.createDataFrame(X)
        from pyspark.sql.functions import array

        df = df.select(array(df.columns).alias("features"))

        mg_model = (
            CPUNearestNeighborsModel(df).setInputCol("features").setK(n_neighbors)
        )

        df_withid, _, knn_df = mg_model.kneighbors(df)

        pdf: pd.DataFrame = df_withid.sort(alias.row_number).toPandas()
        X = np.array(pdf["features"].to_list())

        distances, indices = get_sgnn_res(X, X, n_neighbors)
        assert_knn_equal(knn_df, alias.row_number, distances, indices)

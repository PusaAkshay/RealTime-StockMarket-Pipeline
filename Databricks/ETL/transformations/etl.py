
from pyspark import pipelines as dp
from pyspark.sql.functions import *
from pyspark.sql.types import *

# PATHS
bronze_path = "abfss://bronze@stockmarket.dfs.core.windows.net/stocks/"

# BRONZE TABLE 
@dp.table(name="bronze_stocks")
@dp.expect_all_or_drop({"rule_1": "ticker IS NOT NULL"})
def bronze_stocks():
    df = spark.readStream \
        .format("delta") \
        .load(bronze_path) \
        .withColumn("_load_timestamp", current_timestamp())

    df = df.select(
        col("ticker").cast(StringType()),
        col("open_price").cast(DoubleType()),
        col("high_price").cast(DoubleType()),
        col("low_price").cast(DoubleType()),
        col("current_price").cast(DoubleType()),
        col("close_price").cast(DoubleType()),
        col("volume").cast(LongType()),
        col("change").cast(DoubleType()),
        col("change_pct").cast(DoubleType()),
        col("timestamp").cast(TimestampType()),
        col("_load_timestamp")
    )
    return df


# SILVER TABLE 
silver_rules = {
    "rule_1": "ticker IS NOT NULL",
    "rule_2": "current_price IS NOT NULL",
    "rule_3": "current_price > 0",
    "rule_4": "timestamp IS NOT NULL",
    "rule_5": "volume >= 0"
}

@dp.table(name="silver_stocks")
@dp.expect_all_or_drop(silver_rules)
def silver_stocks():
    df = dp.read_stream("bronze_stocks")

    # Clean change_pct
    df = df.withColumn("change_pct",
        regexp_replace(col("change_pct"), "%", "")
        .cast(DoubleType())
    )

    # Add date column
    df = df.withColumn("trade_date",
        col("timestamp").cast(DateType())
    )

    # Add trade hour
    df = df.withColumn("trade_hour",
        hour(col("timestamp"))
    )

    return df


# GOLD TABLE 
gold_rules = {
    "rule_1": "ticker IS NOT NULL",
    "rule_2": "current_price > 0"
}

@dp.table(name="gold_stocks")
@dp.expect_all_or_drop(gold_rules)
def gold_stocks():
    df = dp.read("silver_stocks")

    # Dedup by ticker + timestamp
    df = df.dropDuplicates(["ticker", "trade_date"])

    # df = df.dropDuplicates(["ticker", "current_price", "trade_date"])

    # Price change category
    df = df.withColumn("price_change_category",
        when(col("change_pct") >= 2.0,  lit("Big Gain"))
        .when(col("change_pct") >= 0.0,  lit("Gain"))
        .when(col("change_pct") >= -2.0, lit("Loss"))
        .otherwise(lit("Big Loss"))
    )

    # Volatility
    df = df.withColumn("volatility",
        round(col("high_price") - col("low_price"), 2)
    )

    # Price range %
    df = df.withColumn("price_range_pct",
        round(
            (col("high_price") - col("low_price"))
            / col("low_price") * 100, 2
        )
    )

    # Volume category
    df = df.withColumn("volume_category",
        when(col("volume") >= 50000000, lit("High"))
        .when(col("volume") >= 10000000, lit("Medium"))
        .otherwise(lit("Low"))
    )

    # Market status
    df = df.withColumn("market_status",
        when(col("change_pct") >= 0, lit("Bull"))
        .otherwise(lit("Bear"))
    )

    return df

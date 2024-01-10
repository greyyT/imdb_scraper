from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pyspark.sql import SparkSession

from database import get_db
from models import Movie as ModelMovie
from ml_models import search

app = FastAPI()

origins = ["http://localhost:3000"]

# to avoid csrftoken error
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# create spark application
spark = (
    SparkSession.builder.appName("SparkTFIDF")
    .master("spark://192.168.194.64:7077")
    .config("spark.executor.memory", "8g")
    .getOrCreate()
)

sc = spark.sparkContext

# read ifidf
ifidf_path = "../pipeline_data_platform/data/model/tfidf.parquet"
tfidf = spark.read.parquet(ifidf_path)


@app.get("/")
def index():
    return {"message": "Hello, world!"}


@app.get("/movies")
def get_movies(
    page: int = Query(1), size: int = Query(20), db: Session = Depends(get_db)
):
    offset = (page - 1) * size
    movies = db.query(ModelMovie).offset(offset).limit(size).all()

    total_records = db.query(ModelMovie).count()
    total_pages = (
        total_records // size + 1
        if total_records % size != 0
        else total_records // size
    )

    return {
        "data": movies,
        "page": page,
        "size": size,
        "totalPages": total_pages,
        "totalRecords": total_records,
    }


@app.get("/movies/{id}")
def get_movie(id: str, db: Session = Depends(get_db)):
    movie = db.query(ModelMovie).filter(ModelMovie.movie_id == id).first()

    return movie


@app.get("/search")
def search_movie(q: str = Query(), db: Session = Depends(get_db)):
    movie_titles = search(spark, tfidf, q, 10)

    movies = []
    
    for title in movie_titles:
        movie = db.query(ModelMovie).filter(ModelMovie.title == title).first()
        movies.append(movie)

    return movies
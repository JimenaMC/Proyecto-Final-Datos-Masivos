# -*- coding: utf-8 -*-
"""Proyecto Datos Masivos.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1jTSjwyaSUY0dJFdfhLfwlQjlMTLLPNSZ
"""

import pandas as pd
import numpy as np

from google.colab import drive
drive.mount('/content/drive')

juegos = pd.read_csv('/content/drive/MyDrive/CDD/7mo/Big Data/juegos.csv')
reviews = pd.read_csv('/content/drive/MyDrive/CDD/7mo/Big Data/reviews.csv')

!mkdir ~/.kaggle

import kagglehub

# Download latest version
path = kagglehub.dataset_download("mohamedtarek01234/steam-games-reviews-and-rankings")

print("Path to dataset files:", path)

!ls /root/.cache/kagglehub/datasets/mohamedtarek01234/steam-games-reviews-and-rankings/versions/1

"""# Lectura"""

games_description = pd.read_csv('/root/.cache/kagglehub/datasets/mohamedtarek01234/steam-games-reviews-and-rankings/versions/1/games_description.csv')
games_description

games_ranking = pd.read_csv('/root/.cache/kagglehub/datasets/mohamedtarek01234/steam-games-reviews-and-rankings/versions/1/games_ranking.csv')
games_ranking

"""# Filtrado Demográfico"""

games_ranking['game_name'].duplicated().sum()

def demographic_recommendation(genre: str = None, rank_type: str = None, num_games: int = 5):
  recommendations = games_ranking.copy()
  if genre and genre not in recommendations['genre'].unique():
    print('Género no encontrado')
    return None

  if genre:
    recommendations = recommendations[recommendations['genre'] == genre]

  if rank_type and rank_type not in recommendations['rank_type'].unique():
    print('Tipo de ranking no encontrado')
    return None

  if rank_type:
    recommendations = recommendations[recommendations['rank_type'] == rank_type]

  recommendations = recommendations.sort_values(by= 'rank', ascending=True).drop_duplicates(subset='game_name')
  return recommendations.head(num_games).drop(columns=['rank_type', 'rank'])

demographic_recommendation(num_games=5)

demographic_recommendation(genre= 'Action', num_games=5)

demographic_recommendation(genre= 'Simulation')

demographic_recommendation(genre= 'Adventure', rank_type='Revenue')

"""# Content-based recommendation"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Iterable

games_description = games_description.drop(columns = ['link', 'long_description'])

games_description.info()

games_description.columns

import re
listas = ['genres', 'minimum_system_requirement',
       'recommend_system_requirement', 'developer',
       'publisher']
for col in listas:
    games_description[col] = games_description[col].\
          apply(lambda x: re.sub(r'[^\w\s0-9,-]', '', str(x))\
             .split(', '))

for col in listas:
  games_description[col] = games_description[col]\
      .apply(lambda x: [y.strip() if len(x)>0 else ['None'] for y in x])
games_description

from sklearn.preprocessing import MultiLabelBinarizer

binarizers = {}
dummies = pd.DataFrame()
for col in listas:
  binarizers[col] = dict(
      binarizer = MultiLabelBinarizer()
  )
  dummies = pd.concat([dummies,
                       pd.DataFrame(
                           data= binarizers[col]['binarizer'].fit_transform(games_description[col]),
                           columns=[col+'_'+x for x in binarizers[col]['binarizer'].classes_])],
                      axis=1)

dummies = dummies.set_index(games_description.index)
dummies

muy_vacias = [x for x in dummies.columns if (np.mean(dummies[x]) < 0.05)]
dummies = dummies.drop(columns=muy_vacias)
dummies.shape

games_description = games_description.drop(columns=listas)

def limpiar(x: str):
  x = re.sub(r'\d+%', '', x)
  x = re.sub(r'[^0-9]', '', x)
  if not x:
    return 0
  return int(x)

limpiar('(81% of 62,791) All Time')

games_description['number_of_reviews_from_purchased_people'] = games_description['number_of_reviews_from_purchased_people']\
  .apply(limpiar)

games_description['number_of_english_reviews'] = games_description['number_of_english_reviews']\
  .apply(limpiar)

rating = {
          'Overwhelmingly Positive': 4,
          'Very Positive': 3,
          'Mostly Positive': 2,
          'Positive': 1,
          'Mixed': 0,
          'Mostly Negative': -2,
          'Very Negative': -4,
          }

games_description['overall_player_rating'] = games_description['overall_player_rating'].map(rating).fillna(0)

games_description

tfidf = TfidfVectorizer(stop_words='english', max_features=100)
tfidf_matrix = tfidf.fit_transform(games_description['short_description'].fillna(''))

tfidf_matrix.shape

tfidf_df = pd.DataFrame(tfidf_matrix.toarray(), columns=tfidf.get_feature_names_out())
tfidf_df

games_description.dtypes

# Escalar variables
from sklearn.preprocessing import MinMaxScaler
mms = MinMaxScaler()

include = ['overall_player_rating', 'number_of_reviews_from_purchased_people', 'number_of_english_reviews']
X = mms.fit_transform(games_description[include])
X = pd.DataFrame(X, columns=include)

content_recommendation_df = pd.concat([X,
                                       tfidf_df,
                                       dummies], axis=1)
content_recommendation_df

# Distancia coseno
cosine_sim = cosine_similarity(content_recommendation_df, content_recommendation_df)
cosine_sim

games_description

def content_recommendation(game_name: str | Iterable, num_games: int = 5):
    if not game_name or game_name not in games_description['name'].values:
        print('Juego no encontrado')
        return None

    # Obtén el índice del juego que coincide con el AppID
    idx = games_description[games_description['name'] == game_name].index[0]

    # Calcula los puntajes de similitud
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1:num_games+1]

    # Obtén los índices de los juegos más similares
    game_indices = [i[0] for i in sim_scores]
    recommendations = games_description[['name']].iloc[game_indices]
    recommendations['similarity_score'] = [i[1] for i in sim_scores]
    # Retorna los AppIDs y nombres de los juegos más similares
    return recommendations

content_recommendation('Grand Theft Auto V')

content_recommendation('Warhammer 40,000: Space Marine 2')

content_recommendation('Cyberpunk 2077')

"""# Factores"""

!pip install --upgrade factor_analyzer

from factor_analyzer import FactorAnalyzer

# Paso 1: Verificar si los datos son adecuados para análisis factorial
from factor_analyzer.factor_analyzer import calculate_bartlett_sphericity, calculate_kmo

bartlett_test, bartlett_p_value = calculate_bartlett_sphericity(content_recommendation_df)
print("Prueba de Bartlett:")
print(f"Estadístico: {bartlett_test}, p-valor: {bartlett_p_value}")

kmo_all, kmo_model = calculate_kmo(content_recommendation_df)
print("\nMedida KMO (Kaiser-Meyer-Olkin):")
print(f"KMO general: {kmo_model}")

# Paso 2: Aplicar Análisis Factorial
factores = 20
fa = FactorAnalyzer(n_factors=factores, rotation='varimax')
fa.fit(content_recommendation_df)

# Graficar resultados
import matplotlib.pyplot as plt
ev, v = fa.get_eigenvalues()

# Graficamos la solución
plt.scatter(range(1,content_recommendation_df.shape[1]+1),ev)
plt.plot(range(1,content_recommendation_df.shape[1]+1),ev)
plt.title('Scree Plot')
plt.xlabel('Factors')
plt.ylabel('Eigenvalue')
plt.hlines(y = 1, xmax=1, xmin=7, color='r', linestyles='--')
plt.show()

# Verificar cargas factoriales
factor_loadings = pd.DataFrame(fa.loadings_, columns=[f"Factor {i}" for i in range(factores)], index=content_recommendation_df.columns)
print("\nCargas Factoriales:")
print(factor_loadings)

# Paso 3: Verificar comunalidades (qué tan bien están explicadas las variables)
comunalidades = pd.DataFrame(fa.get_communalities(), columns=["Comunalidad"], index=content_recommendation_df.columns)
print("\nComunalidades:")
print(comunalidades)

# Paso 4: Varianza explicada por los factores
varianza_explicada = pd.DataFrame(
    fa.get_factor_variance(),
    index=["Varianza explicada", "Varianza proporcional", "Varianza acumulada"],
    columns=[f"Factor {i}" for i in range(factores)]
)
print("\nVarianza explicada por cada factor:")
print(varianza_explicada)

for i in range(factores):
  print(f"Variables en el factor {i+1}:")
  variables = factor_loadings.iloc[:, i].sort_values(ascending=False).where(lambda x: abs(x)>0.5).dropna()
  if len(variables) <= 1:
    variables = factor_loadings.iloc[:, i].sort_values(ascending=False, key=lambda x: abs(x)).head(3)
  print(variables, '\n\n')

content_recommendation_df.shape

"""# Colaborative Filtering"""

reviews = pd.read_csv('/root/.cache/kagglehub/datasets/mohamedtarek01234/steam-games-reviews-and-rankings/versions/1/steam_game_reviews.csv')
reviews

reviews.columns

reviews.dropna(inplace=True)
reviews['username'] = reviews['username'].apply(lambda x: x.split('\n')[0])

recommendation = {
    'Recommended': 1,
    'Not Recommended': 0
}

reviews['recommendation'] = reviews['recommendation'].map(recommendation)

reviews

reviews.duplicated(subset= ['game_name', 'username']).sum()

reviews.drop_duplicates(subset= ['game_name', 'username'], inplace=True)

reviews

# reviews = reviews.pivot(index='game_name', columns='username', values='recommendation')
# reviews

# reviews.fillna(0, inplace=True)
# reviews

!pip install scikit-surprise

reviews.columns

from surprise import SVD
from surprise import Dataset, Reader
from surprise.model_selection import train_test_split
from surprise import accuracy

# Crear el dataset para Surprise
reader = Reader(rating_scale=(0, 1))  # Ajusta la escala de las valoraciones
data = Dataset.load_from_df(reviews[['username', 'game_name', 'recommendation']], reader)

# Dividir los datos en entrenamiento y prueba
trainset, testset = train_test_split(data, test_size=0.2, random_state=42)

# Entrenar el modelo SVD
model = SVD()
model.fit(trainset)

# Evaluar el modelo
predictions = model.test(testset)
print("RMSE:", accuracy.rmse(predictions))

def collab_filter_recommendation(username: str, num_games: int = 5):
    all_games = reviews['game_name'].unique()
    rated_games = reviews[reviews['username'] == username]
    print(f'Juegos calificados por {username}:')
    display(rated_games[['game_name', 'recommendation']])
    unrated_games = [game for game in all_games if game not in rated_games['game_name'].values]

    recommendations = [
        (game_name, model.predict(username, game_name).est) for game_name in unrated_games
    ]
    recommendations = sorted(recommendations, key=lambda x: x[1], reverse=True)[:num_games]

    # Mostrar los mejores juegos recomendados
    print(f"\nTop {num_games} juegos recomendados para {username}:")
    for game_name, score in recommendations:
        print(f"Juego ID: {game_name}, Puntuación estimada: {score:.2f}")

collab_filter_recommendation('Alex')

collab_filter_recommendation('Shadow')

collab_filter_recommendation('tankanidis')

collab_filter_recommendation('Saul')

collab_filter_recommendation('Sebastian')

reviews.sample(10)

reviews['username'].value_counts()

games_ranking.shape

games_ranking['genre'].value_counts()

games_ranking['rank_type'].value_counts()


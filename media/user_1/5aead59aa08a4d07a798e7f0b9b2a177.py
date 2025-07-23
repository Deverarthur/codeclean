@app.route(‘/movies’, methods=[‘GET’]) 

def fetch_movies(): 

    year = request.args.get(‘year’) 

    if year is None: 

        return jsonify({‘error’: ‘Year parameter is missing.’}), 400 

    connection = sqlite3.connect(‘movies.db’) 

    cursor = connection.cursor() 

    query = « SELECT title FROM movies WHERE year = ‘%s' » % year 

    cursor.execute(query) 

    movies = [row[0] for row in cursor.fetchall()] 

    connection.close() 

    return jsonify({‘movies’: movies})


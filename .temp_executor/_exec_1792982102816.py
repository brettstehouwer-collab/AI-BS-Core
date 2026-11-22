import duckdb, json
q = 'SELECT email FROM rec_debut\nWHERE is_parent = 1;'
res = duckdb.sql(q).fetchall()
print(json.dumps(res, indent=2, default=str))

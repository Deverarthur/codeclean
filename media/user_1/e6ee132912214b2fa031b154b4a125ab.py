user_input = input("Enter a math expression: ")
result = eval(user_input)  # ⚠️ Unsafe: eval executes any code
print(f"Result: {result}")


import sqlite3

conn = sqlite3.connect('example.db')
cursor = conn.cursor()

username = input("Enter your username: ")
query = f"SELECT * FROM users WHERE username = '{username}'"
cursor.execute(query)  # ⚠️ Vulnerable: directly using unsanitized input!

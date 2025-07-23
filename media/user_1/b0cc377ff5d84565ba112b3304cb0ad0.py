user_input = input("Enter a math expression: ")
result = eval(user_input)  # ⚠️ Unsafe: eval executes any code
print(f"Result: {result}")

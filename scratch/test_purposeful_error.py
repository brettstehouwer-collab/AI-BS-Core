def buggy_function():
    # Dictionary key mutation during iteration
    data = {"key1": "value1", "key2": "value2", "key3": "value3"}
    
    for key in data.keys():
        if key == "key2":
            data["new_key"] = "new_value"  # This will cause a RuntimeError in Python 3
            print(undef_var)  # undefined variable catch

if __name__ == "__main__":
    print("Running test_purposeful_error.py...")
    buggy_function()

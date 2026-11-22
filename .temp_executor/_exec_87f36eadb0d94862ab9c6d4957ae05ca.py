def check_unreal_setup():
    # Ensure the paths are correct and accessible
    if not work.exists():
        print("Work path does not exist.")
    if not art.exists():
        print("Art path does not exist.")
    if not ue.exists():
        print("Unreal content path does not exist.")
    if not target.exists():
        print("Target path does not exist.")
    
    # Additional checks can be added here based on specific needs

check_unreal_setup()
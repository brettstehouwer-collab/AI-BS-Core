#!/usr/bin/env python3
"""Quick Phase 4 test without Unicode issues"""
import sys
sys.path.insert(0, r'C:\Users\footb\AI-BS_Matrix')

def test_hypervisor_controller():
    print("\n" + "="*80)
    print("PHASE 4 STAGE 1: HYPERVISOR CONTROLLER OPERATIONAL TEST")
    print("="*80 + "\n")

    try:
        print("[1] Importing hypervisor controller...")
        from hypervisor_controller_daemon import get_hypervisor_controller, VMConfig
        print("    SUCCESS - Docker client initialized\n")
        
        print("[2] Getting controller instance...")
        controller = get_hypervisor_controller()
        print("    SUCCESS - Controller ready\n")
        
        print("[3] Booting test VM...")
        config = VMConfig(
            vm_id="phase4-test-001",
            memory_mb=256,
            cpu_cores=1,
        )
        boot_result = controller.boot_vm(config)
        print(f"    Boot status: {boot_result['status']}")
        print(f"    VM ID: {boot_result['vm_id']}")
        print(f"    Container ID: {boot_result['container_id'][:12]}")
        
        vm_id = boot_result['vm_id']
        
        print("\n[4] Executing command in VM...")
        import time
        time.sleep(2)  # Wait for container to stabilize
        
        exec_result = controller.execute_in_vm(vm_id, "echo 'Phase 4 Operational'")
        print(f"    Exit code: {exec_result['exit_code']}")
        print(f"    Output: {exec_result['stdout'].strip()}")
        
        print("\n[5] Getting VM status...")
        status = controller.get_vm_status(vm_id)
        print(f"    Status: {status['status']}")
        print(f"    Memory: {status['memory_mb']} MB")
        print(f"    CPUs: {status['cpu_cores']}")
        
        print("\n[6] Listing active VMs...")
        vms = controller.list_vms()
        print(f"    Active VMs: {vms['count']}")
        
        print("\n[7] Shutting down VM...")
        shutdown = controller.shutdown_vm(vm_id)
        print(f"    Shutdown status: {shutdown['status']}")
        
        print("\n" + "="*80)
        print("SUCCESS - PHASE 4 STAGE 1 IS OPERATIONAL")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        raise e

if __name__ == '__main__':
    test_hypervisor_controller()

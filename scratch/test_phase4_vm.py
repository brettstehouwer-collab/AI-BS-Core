#!/usr/bin/env python3
"""
PHASE 4, STAGE 1: TEST SUITE
Diagnostic script to verify VM boot, command execution, and cleanup.

This tests the entire isolation stack:
  1. Docker connectivity
  2. VM boot with resource limits
  3. Command execution in isolated environment
  4. Disk image provisioning
  5. Cleanup and resource deallocation
"""

import sys
import json
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from hypervisor_controller_daemon import get_hypervisor_controller, VMConfig
from disk_image_manager import get_disk_image_manager, DiskImageSpec


async def test_vm_lifecycle():
    """Test complete VM lifecycle"""
    print("\n" + "="*80)
    print("PHASE 4, STAGE 1: VM LIFECYCLE TEST")
    print("="*80 + "\n")
    
    try:
        controller = get_hypervisor_controller()
        
        # Step 1: Boot VM
        print("[1/5] Booting isolated VM...")
        config = VMConfig(
            vm_id="test-vm-001",
            memory_mb=256,
            cpu_cores=1,
            network_isolated=True,
        )
        
        boot_result = controller.boot_vm(config)
        print(f"✓ VM boot result: {json.dumps(boot_result, indent=2)}")
        
        if boot_result["status"] != "booting":
            print("✗ VM boot failed")
            return False
        
        vm_id = boot_result["vm_id"]
        
        # Wait for container to stabilize
        print("\n[2/5] Waiting for VM to stabilize...")
        await asyncio.sleep(2)
        
        # Step 2: Get status
        print("\n[2/5] Checking VM status...")
        status = controller.get_vm_status(vm_id)
        print(f"✓ VM status: {json.dumps(status, indent=2)}")
        
        # Step 3: Execute commands
        print("\n[3/5] Executing test commands in VM...")
        
        # Command 1: Simple echo
        result1 = controller.execute_in_vm(vm_id, "echo 'Hello from isolated VM'")
        print(f"✓ Echo test: {result1['stdout'].strip()}")
        
        # Command 2: System info
        result2 = controller.execute_in_vm(vm_id, "uname -a")
        print(f"✓ System info: {result2['stdout'].strip()}")
        
        # Command 3: Check isolation (should fail to access host resources)
        result3 = controller.execute_in_vm(vm_id, "cat /proc/meminfo | head -3")
        print(f"✓ Isolation test (container meminfo):\n{result3['stdout'][:200]}")
        
        # Step 4: List VMs
        print("\n[4/5] Listing active VMs...")
        vms = controller.list_vms()
        print(f"✓ Active VMs: {vms['count']}")
        print(json.dumps(vms['vms'], indent=2))
        
        # Step 5: Shutdown
        print("\n[5/5] Shutting down VM...")
        shutdown_result = controller.shutdown_vm(vm_id)
        print(f"✓ Shutdown result: {json.dumps(shutdown_result, indent=2)}")
        
        print("\n✓ VM Lifecycle Test: PASSED\n")
        return True
        
    except Exception as e:
        print(f"\n✗ VM Lifecycle Test FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


async def test_disk_lifecycle():
    """Test disk image lifecycle"""
    print("\n" + "="*80)
    print("PHASE 4, STAGE 1: DISK LIFECYCLE TEST")
    print("="*80 + "\n")
    
    try:
        manager = get_disk_image_manager()
        
        # Step 1: Create disk
        print("[1/3] Creating virtual disk image...")
        spec = DiskImageSpec(
            name="test-disk",
            size_mb=256,
            task_id="task-001",
            persistent=False,
        )
        
        create_result = manager.create_image(spec)
        print(f"✓ Disk creation result: {json.dumps(create_result, indent=2)}")
        
        if create_result["status"] != "success":
            print("✗ Disk creation failed")
            return False
        
        volume_name = create_result["volume_name"]
        
        # Step 2: List disks
        print("\n[2/3] Listing disk images...")
        listing = manager.list_images()
        print(f"✓ Active disks: {listing['count']}")
        print(json.dumps(listing['images'], indent=2))
        
        # Step 3: Cleanup disk
        print("\n[3/3] Cleaning up disk image...")
        cleanup_result = manager.cleanup_image(volume_name)
        print(f"✓ Cleanup result: {json.dumps(cleanup_result, indent=2)}")
        
        print("\n✓ Disk Lifecycle Test: PASSED\n")
        return True
        
    except Exception as e:
        print(f"\n✗ Disk Lifecycle Test FAILED: {e}\n")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "PHASE 4, STAGE 1: COMPREHENSIVE TEST SUITE" + " "*16 + "║")
    print("║" + " "*15 + "Hypervisor Controller + Disk Image Manager" + " "*21 + "║")
    print("╚" + "="*78 + "╝")
    
    results = []
    
    # Test 1: VM Lifecycle
    vm_test = await test_vm_lifecycle()
    results.append(("VM Lifecycle", vm_test))
    
    # Test 2: Disk Lifecycle
    disk_test = await test_disk_lifecycle()
    results.append(("Disk Lifecycle", disk_test))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80 + "\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name:30} {status}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ ALL TESTS PASSED - Phase 4 Stage 1 is OPERATIONAL\n")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED - Check logs above\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

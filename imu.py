import asyncio
from bleak import BleakScanner, BleakClient
import time
from pylsl import StreamInfo, StreamOutlet  # Import LSL components

IMU_SERVICE_UUID = "19B10000-E8F2-537E-4F6C-D104768A1214"
IMU_CHARACTERISTIC_UUID = "19B10001-E8F2-537E-4F6C-D104768A1214"

# Global variables for rate calculation and LSL outlet
sample_count = 0
start_time = None
lsl_outlet = None  # LSL outlet for streaming IMU data

def imu_callback(_, data):
    global sample_count, start_time, lsl_outlet
    
    try:
        # Skip if data is empty
        if not data:
            return

        # Parse the IMU data (expected 6 channels: 3 accel and 3 gyro)
        values = [float(x) for x in data.decode().split(',')]
        if len(values) < 6:
            print("Received data with insufficient channels.")
            return

        # Print the channels for debugging
        print(f"Accel (x,y,z): {values[0:3]}")
        print(f"Gyro (x,y,z): {values[3:6]}")

        # Push the parsed sample to the LSL stream
        if lsl_outlet:
            lsl_outlet.push_sample(values)
        
        # Rate calculation: initialize start time on the first callback
        if start_time is None:
            start_time = time.time()
        
        # Count this sample
        sample_count += 1
        
        # Calculate and print sample rate every second
        current_time = time.time()
        elapsed_time = current_time - start_time
        if elapsed_time >= 1.0:
            rate = sample_count / elapsed_time
            print(f"IMU Sample Rate: {rate:.2f} Hz")
            # Reset counter and start time for the next interval
            sample_count = 0
            start_time = current_time
            
    except Exception as e:
        print(f"Error in callback: {e}")

async def main():
    global lsl_outlet
    # Create LSL stream info and outlet:
    # - Stream name: IMU_Stream
    # - Type: IMU
    # - 6 channels
    # - Sampling rate 0 (irregular)
    # - Data type: float32
    # - A unique source id (here 'imu12345')
    info = StreamInfo('IMU_Stream', 'IMU', 6, 0, 'float32', 'imu12345')
    lsl_outlet = StreamOutlet(info)
    print("LSL stream created")

    # Discover BLE devices and connect to the Arduino
    devices = await BleakScanner.discover()
    for d in devices:
        if d.name == "Arduino":
            print(f"Found {d.name}")
            async with BleakClient(d.address) as client:
                print("Connected!")
                await client.start_notify(IMU_CHARACTERISTIC_UUID, imu_callback)
                # Wait indefinitely (or until disconnect / keyboard interrupt)
                await asyncio.get_event_loop().create_future()
    else:
        print("Arduino not found")

async def scan_devices():
    print("Scanning for BLE devices...")
    devices = await BleakScanner.discover()
    print("\nDevices found:")
    print("-" * 50)
    for d in devices:
        print(f"Name: {d.name}")
        print(f"Address: {d.address}")
        print(f"Details: {d}")
        print("-" * 50)

if __name__ == '__main__':
    asyncio.run(main())

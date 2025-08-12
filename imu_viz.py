import time
import pygame
from collections import deque
from pylsl import StreamInlet, resolve_stream

# Constants (same as in ble_imu.py)
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 800           # Increased height
PADDING = 50
PLOT_HEIGHT = (WINDOW_HEIGHT - 4 * PADDING) // 2  # Adjusted plot height
WINDOW_SIZE = 100
SCALE_FACTOR = 50

# Colors
BLACK  = (0, 0, 0)
WHITE  = (255, 255, 255)
RED    = (255, 0, 0)
GREEN  = (0, 255, 0)
BLUE   = (0, 0, 255)
YELLOW = (255, 255, 0)

class IMUVisualizer:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("IMU LSL Data Visualization")
        
        # Data storage using deque for a fixed-size window
        self.acc_x = deque([0] * WINDOW_SIZE, maxlen=WINDOW_SIZE)
        self.acc_y = deque([0] * WINDOW_SIZE, maxlen=WINDOW_SIZE)
        self.acc_z = deque([0] * WINDOW_SIZE, maxlen=WINDOW_SIZE)
        self.gyro_x = deque([0] * WINDOW_SIZE, maxlen=WINDOW_SIZE)
        self.gyro_y = deque([0] * WINDOW_SIZE, maxlen=WINDOW_SIZE)
        self.gyro_z = deque([0] * WINDOW_SIZE, maxlen=WINDOW_SIZE)
        
        self.font = pygame.font.Font(None, 24)
        self.refresh_rate = 0.0  # Displayed refresh rate
        
        # Y-axis ranges
        self.acc_range = 2    # ±2g for accelerometer
        self.gyro_range = 250  # ±250 deg/s for gyroscope

    def update_data(self, values):
        # Expecting values to be a list of at least 6 floats
        self.acc_x.append(values[0])
        self.acc_y.append(values[1])
        self.acc_z.append(values[2])
        self.gyro_x.append(values[3])
        self.gyro_y.append(values[4])
        self.gyro_z.append(values[5])

    def draw_y_axis_labels(self, y_offset, range_val, title):
        # Draw title above the plot
        title_surface = self.font.render(title, True, WHITE)
        self.screen.blit(title_surface, (PADDING, y_offset - PLOT_HEIGHT - 30))
        
        # Draw y-axis scale labels (4 steps)
        steps = 4
        for i in range(steps + 1):
            val = range_val * (2 * i / steps - 1)
            y_pos = y_offset - (val * PLOT_HEIGHT / range_val)
            label = self.font.render(f"{val:.1f}", True, WHITE)
            self.screen.blit(label, (5, y_pos - 10))

    def draw_plot(self, data, y_offset, title, color, range_val):
        # Draw vertical axis line
        pygame.draw.line(self.screen, WHITE, 
                         (PADDING, y_offset - PLOT_HEIGHT), 
                         (PADDING, y_offset + PLOT_HEIGHT), 1)
        # Draw horizontal axis line
        pygame.draw.line(self.screen, WHITE, 
                         (PADDING, y_offset), 
                         (WINDOW_WIDTH - PADDING, y_offset), 1)
        
        # Draw legend text on the right side of the plot
        legend = self.font.render(title, True, color)
        legend_x = WINDOW_WIDTH - PADDING - 100  # Right-side positioning
        self.screen.blit(legend, (legend_x, y_offset - PLOT_HEIGHT + 20 * (color[0] // 255)))
        
        # Generate list of points for the plot line
        points = []
        for i, value in enumerate(data):
            x = PADDING + (i * (WINDOW_WIDTH - 2 * PADDING) / WINDOW_SIZE)
            scaled_y = (value * PLOT_HEIGHT / range_val)
            y = y_offset - scaled_y
            points.append((x, y))
            
        if len(points) > 1:
            pygame.draw.lines(self.screen, color, False, points, 2)

    def draw(self):
        # Clear screen
        self.screen.fill(BLACK)
        
        # Display refresh rate at top-right
        rate_text = self.font.render(f"Refresh Rate: {self.refresh_rate:.1f} Hz", True, YELLOW)
        self.screen.blit(rate_text, (WINDOW_WIDTH - 200, 10))
        
        # Draw accelerometer plot
        acc_y_offset = PADDING + PLOT_HEIGHT
        self.draw_y_axis_labels(acc_y_offset, self.acc_range, "Accelerometer (g)")
        self.draw_plot(self.acc_x, acc_y_offset, "X-axis", RED, self.acc_range)
        self.draw_plot(self.acc_y, acc_y_offset, "Y-axis", GREEN, self.acc_range)
        self.draw_plot(self.acc_z, acc_y_offset, "Z-axis", BLUE, self.acc_range)
        
        # Draw gyroscope plot
        gyro_y_offset = 3 * PADDING + 2 * PLOT_HEIGHT  # Extra spacing between plots
        self.draw_y_axis_labels(gyro_y_offset, self.gyro_range, "Gyroscope (deg/s)")
        self.draw_plot(self.gyro_x, gyro_y_offset, "X-axis", RED, self.gyro_range)
        self.draw_plot(self.gyro_y, gyro_y_offset, "Y-axis", GREEN, self.gyro_range)
        self.draw_plot(self.gyro_z, gyro_y_offset, "Z-axis", BLUE, self.gyro_range)
        
        pygame.display.flip()

def main():
    print("Resolving IMU_Stream LSL stream...")
    streams = resolve_stream('name', 'IMU_Stream')
    if not streams:
        print("No IMU_Stream found! Make sure your BLE script is running and streaming LSL data.")
        return

    inlet = StreamInlet(streams[0])
    print("IMU_Stream resolved. Listening for samples...")
    
    viz = IMUVisualizer()
    
    # For refresh rate calculation
    frame_count = 0
    start_time = time.time()
    
    # Main loop (no delay calls; runs as fast as possible)
    while True:
        # Use non-blocking call so there is no artificial delay
        sample, timestamp = inlet.pull_sample(timeout=0.0)
        if sample is not None:
            if len(sample) >= 6:
                viz.update_data(sample)
                frame_count += 1
                current_time = time.time()
                elapsed_time = current_time - start_time
                if elapsed_time >= 1.0:
                    viz.refresh_rate = frame_count / elapsed_time
                    frame_count = 0
                    start_time = current_time
            else:
                print("Received sample with insufficient channels:", sample)

        # Process Pygame events for graceful exit
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
        
        viz.draw()
        # Removed clock.tick() to avoid FPS limitation and sleep delays.

if __name__ == "__main__":
    main() 

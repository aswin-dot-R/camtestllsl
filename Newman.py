import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import cv2

# Add the parent directory to the path so we can import video_annotator
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xdf_reader import XDFReader
from ui_components import StreamFrame, InfoFrame, ControlPanel
from export_utils import export_stream_to_csv

class XDFApp:
    def __init__(self, root):
        self.root = root
        self.root.title("XDF Reader Application")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        self.xdf_reader = XDFReader()
        self.current_file = None
        self.streams = None
        self.header = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # Create main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top control panel
        self.control_panel = ControlPanel(main_frame, self.open_file, self.refresh_data)
        self.control_panel.pack(fill=tk.X, pady=(0, 10))
        
        # Add video navigation controls
        video_frame = ttk.LabelFrame(main_frame, text="Video Navigation", padding="5")
        video_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Video file selection
        ttk.Label(video_frame, text="Video File:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.video_path_var = tk.StringVar()
        self.video_path_var.set("No video file selected")
        ttk.Label(video_frame, textvariable=self.video_path_var, wraplength=400).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ttk.Button(video_frame, text="Select Video", command=self.select_video_file).grid(row=0, column=2, padx=5, pady=5)
        
        # Time offset adjustment (between XDF and video)
        ttk.Label(video_frame, text="Time Offset (s):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.time_offset_var = tk.DoubleVar(value=0.0)
        ttk.Entry(video_frame, textvariable=self.time_offset_var, width=10).grid(row=1, column=1, padx=5, pady=5, sticky="w")
        ttk.Label(video_frame, text="(positive if video starts after XDF recording)").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        
        # Create paned window for resizable sections
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - stream list and info
        left_frame = ttk.Frame(paned, padding="5")
        paned.add(left_frame, weight=1)
        
        # Info frame shows file details and header
        self.info_frame = InfoFrame(left_frame)
        self.info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Streams list
        streams_label = ttk.Label(left_frame, text="Available Streams:", font=("", 12, "bold"))
        streams_label.pack(fill=tk.X, pady=(0, 5))
        
        streams_frame = ttk.Frame(left_frame)
        streams_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollable streams list
        scroll = ttk.Scrollbar(streams_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.streams_list = tk.Listbox(streams_frame, yscrollcommand=scroll.set, 
                                      font=("", 11), activestyle='dotbox')
        self.streams_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self.streams_list.yview)
        
        self.streams_list.bind("<<ListboxSelect>>", self.on_stream_selected)
        
        # Actions frame
        actions_frame = ttk.LabelFrame(left_frame, text="Actions", padding="5")
        actions_frame.pack(fill=tk.X, pady=(10, 0))
        
        export_btn = ttk.Button(actions_frame, text="Export Selected Stream to CSV", 
                               command=self.export_stream)
        export_btn.pack(fill=tk.X, pady=5)
        
        visualize_btn = ttk.Button(actions_frame, text="Visualize Selected Stream", 
                                  command=self.visualize_selected_stream)
        visualize_btn.pack(fill=tk.X, pady=5)
        
        # Right panel - stream details
        right_frame = ttk.Frame(paned, padding="5")
        paned.add(right_frame, weight=2)
        
        self.stream_frame = StreamFrame(right_frame)
        self.stream_frame.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready. Please open an XDF file.")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, 
                             relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(10, 0))
        
        # Add right-click menu for streams list
        self.stream_popup = tk.Menu(self.root, tearoff=0)
        self.stream_popup.add_command(label="View Stream Info", command=self.view_stream_info)
        self.stream_popup.add_command(label="Export to CSV", command=self.export_stream)
        self.stream_popup.add_separator()
        self.stream_popup.add_command(label="Edit LSL Markers", command=self.edit_selected_marker_stream)
        
        # Bind right-click to streams listbox
        self.streams_list.bind("<Button-3>", self.show_stream_popup)
        
        # Create menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open XDF File", command=self.open_file)
        file_menu.add_command(label="Select Video", command=self.select_video_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.destroy)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Export Selected Stream", command=self.export_stream)
        tools_menu.add_command(label="Advanced Visualization", command=self.advanced_visualize)
        tools_menu.add_separator()
        tools_menu.add_command(label="Edit Marker Stream", command=self.open_marker_editor)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
    
    def open_file(self):
        filename = filedialog.askopenfilename(
            title="Select XDF File",
            filetypes=[("XDF files", "*.xdf"), ("All files", "*.*")]
        )
        
        if not filename:
            return
        
        self.status_var.set(f"Loading file: {filename}")
        self.root.update()
        
        try:
            self.streams, self.header = self.xdf_reader.load_xdf(filename)
            self.current_file = filename
            self.populate_streams_list()
            self.info_frame.update_info(self.current_file, self.header, len(self.streams))
            self.status_var.set(f"Loaded {filename} with {len(self.streams)} streams")
        except Exception as e:
            messagebox.showerror("Error Loading File", f"Failed to load XDF file:\n{e}")
            self.status_var.set("Error loading file.")
    
    def populate_streams_list(self):
        self.streams_list.delete(0, tk.END)
        if not self.streams:
            return
        for i, stream in enumerate(self.streams):
            name = None
            stype = "Unknown"
            if 'info' in stream:
                name = stream['info'].get('name', [None])[0] if 'name' in stream['info'] else None
                stype = stream['info'].get('type', [None])[0] if 'type' in stream['info'] else "Unknown"
            stream_name = name if name else f"Stream #{i+1}"
            self.streams_list.insert(tk.END, f"{i+1}: {stream_name} ({stype})")
    
    def on_stream_selected(self, event):
        """Handle selection of a stream from the list."""
        if not self.streams:
            return
            
        selection = self.streams_list.curselection()
        if not selection:
            return
            
        index = selection[0]
        if index < len(self.streams):
            stream = self.streams[index]
            self.stream_frame.display_stream(stream, index)
            self.status_var.set(f"Displaying stream {index+1}")
            
            # Enable click-to-navigate on data points for this stream
            if hasattr(self, 'video_player') and self.video_player is not None:
                self.stream_frame.enable_timestamp_navigation(self.navigate_to_video_frame)
    
    def export_stream(self):
        """Export the selected stream to CSV."""
        selection = self.streams_list.curselection()
        if not selection or not self.streams:
            messagebox.showinfo("No Selection", "Please select a stream to export.")
            return
        
        index = selection[0]
        if index < len(self.streams):
            stream = self.streams[index]
            stream_info = self.xdf_reader.get_stream_info(stream)
            
            # Generate default filename based on stream name
            default_filename = f"{stream_info['name']}.csv"
            
            # Ask user where to save
            filename = filedialog.asksaveasfilename(
                title="Export Stream to CSV",
                defaultextension=".csv",
                initialfile=default_filename,
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            
            if filename:
                try:
                    self.status_var.set(f"Exporting stream to {filename}...")
                    self.root.update()
                    
                    # Convert stream data to CSV
                    export_stream_to_csv(stream, filename)
                    
                    self.status_var.set(f"Exported stream to {filename}")
                    messagebox.showinfo("Export Complete", 
                                      f"Stream '{stream_info['name']}' was successfully exported to:\n{filename}")
                except Exception as e:
                    messagebox.showerror("Export Error", f"Failed to export stream: {e}")
                    self.status_var.set("Error exporting stream.")

    def visualize_selected_stream(self):
        if not self.streams:
            messagebox.showinfo("No Data", "Please open an XDF file first.")
            return
            
        selection = self.streams_list.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a stream to visualize.")
            return
            
        index = selection[0]
        if index < len(self.streams):
            try:
                from data_visualizer import visualize_stream
                visualize_stream(self.streams[index])
                self.status_var.set("Visualization window opened")
            except Exception as e:
                messagebox.showerror("Visualization Error", f"Failed to visualize stream:\n{e}")
                self.status_var.set("Error visualizing stream.")
    
    def refresh_data(self):
        """Reload the currently open XDF file without prompting."""
        if self.current_file:
            filename = self.current_file
            self.status_var.set(f"Reloading file: {filename}")
            try:
                self.streams, self.header = self.xdf_reader.load_xdf(filename)
                self.populate_streams_list()
                self.info_frame.update_info(filename, self.header, len(self.streams))
                self.status_var.set(f"Reloaded {filename} with {len(self.streams)} streams")
            except Exception as e:
                messagebox.showerror("Error Reloading File", f"Failed to reload XDF file:\n{e}")
                self.status_var.set("Error reloading file.")
        else:
            messagebox.showinfo("No File", "Please open an XDF file first.")

    def select_video_file(self):
        """Select a video file to link with XDF data"""
        video_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video files", "*.mp4 *.avi *.mov"), ("All files", "*.*")]
        )
        
        if not video_path:
            return
        
        self.video_path = video_path
        self.video_path_var.set(os.path.basename(video_path))
        
        # Try to open the video to get properties
        try:
            from video_annotator import VideoAnnotator
            self.video_player = VideoAnnotator(standalone=False)
            self.video_player.open_video_file(video_path)
            self.status_var.set(f"Video loaded: {os.path.basename(video_path)}")
        except Exception as e:
            messagebox.showerror("Error Opening Video", f"Could not open video file: {e}")
            self.video_path_var.set("Error loading video")

    def navigate_to_video_frame(self, timestamp):
        """Navigate to the video frame corresponding to the given XDF timestamp"""
        if not hasattr(self, 'video_player') or self.video_player is None:
            messagebox.showinfo("No Video", "Please select a video file first.")
            return
        
        # Apply time offset
        adjusted_timestamp = timestamp + self.time_offset_var.get()
        
        try:
            # Get video properties
            fps = self.video_player.cap.get(cv2.CAP_PROP_FPS)
            if not fps or fps <= 0:
                fps = 30.0  # fallback
            
            # Find the closest frame
            frame_number = int(adjusted_timestamp * fps)
            
            # Open the video player window if not already open
            if not self.video_player.is_window_open():
                self.video_player.show_window()
            
            # Jump to the frame
            self.video_player.jump_to_frame(frame_number)
            self.status_var.set(f"Navigated to frame {frame_number} (timestamp: {adjusted_timestamp:.3f}s)")
        except Exception as e:
            messagebox.showerror("Navigation Error", f"Could not navigate to timestamp {timestamp}: {e}")

    def edit_stream_markers(self, stream_idx):
        """Open the LSL marker editor for the selected stream."""
        if not self.streams or stream_idx >= len(self.streams):
            messagebox.showinfo("No Stream", "Please select a marker stream to edit.")
            return
        
        # Check if this is a marker stream
        stream = self.streams[stream_idx]
        stream_info = self.xdf_reader.get_stream_info(stream)
        stype = (stream_info.get('type') or '').lower()
        
        if stype not in ['markers', 'marker']:
            messagebox.showinfo("Not a Marker Stream", 
                               f"Selected stream '{stream_info['name']}' is not a marker stream.\n"
                               f"Type: {stream_info['type']}")
            return
        
        # Check if we have a video file selected
        if not hasattr(self, 'video_path') or not self.video_path:
            # Ask if user wants to select a video
            select_video = messagebox.askyesno("No Video", 
                                             "No video file is currently selected. Marker editing works best with video.\n\n"
                                             "Would you like to select a video file now?")
            if select_video:
                self.select_video_file()
            
            # Check again if video was selected
            if not hasattr(self, 'video_path') or not self.video_path:
                messagebox.showinfo("No Video", "Marker editing canceled. Please select a video file first.")
                return
        
        # Import and create the marker editor
        try:
            from lsl_marker_editor import LSLMarkerEditor
            
            # Create the marker editor
            self.marker_editor = LSLMarkerEditor(
                parent=self.root,
                stream=stream,
                video_path=self.video_path,
                time_offset=self.time_offset_var.get()
            )
            
            self.status_var.set(f"Marker editor opened for '{stream_info['name']}' stream")
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not open marker editor: {e}")
            import traceback
            traceback.print_exc()

    def show_stream_popup(self, event):
        """Show the popup menu for the streams list."""
        # Get the index of the item under the mouse
        index = self.streams_list.nearest(event.y)
        if index >= 0:
            self.streams_list.selection_clear(0, tk.END)
            self.streams_list.selection_set(index)
            self.streams_list.activate(index)
            
            # Check if it's a marker stream
            is_marker = False
            if self.streams and index < len(self.streams):
                stream_info = self.xdf_reader.get_stream_info(self.streams[index])
                stype = (stream_info.get('type') or '').lower()
                is_marker = stype in ['markers', 'marker']
            
            # Enable/disable the Edit Markers option
            self.stream_popup.entryconfig("Edit LSL Markers", 
                                        state=tk.NORMAL if is_marker else tk.DISABLED)
            
            # Show the popup menu
            try:
                self.stream_popup.tk_popup(event.x_root, event.y_root)
            finally:
                self.stream_popup.grab_release()

    def edit_selected_marker_stream(self):
        """Edit the currently selected marker stream."""
        selection = self.streams_list.curselection()
        if selection:
            index = selection[0]
            self.edit_stream_markers(index)

    def open_marker_editor(self, marker_stream_idx=None):
        """
        Open the marker editor for the selected marker stream.
        If marker_stream_idx is None, prompt the user to select a marker stream.
        """
        # Guard: must have streams loaded
        if not self.streams:
            messagebox.showinfo("No Streams", "Please open an XDF file first.")
            return

        # If no stream index provided, get from selection or prompt user
        if marker_stream_idx is None:
            selection = self.streams_list.curselection()
            if selection:
                marker_stream_idx = selection[0]
            else:
                # No selection, so find marker streams and let user choose
                marker_streams = []
                for i, stream in enumerate(self.streams):
                    stream_info = self.xdf_reader.get_stream_info(stream)
                    stype = (stream_info.get('type') or '').lower()
                    if stype in ['markers', 'marker']:
                        marker_streams.append((i, stream_info.get('name', f"Stream {i+1}")))
                
                if not marker_streams:
                    messagebox.showinfo("No Marker Streams", "No marker streams found in the XDF file.")
                    return
                    
                # Create dialog to select stream
                select_dialog = tk.Toplevel(self.root)
                select_dialog.title("Select Marker Stream")
                select_dialog.geometry("400x300")
                select_dialog.transient(self.root)
                select_dialog.grab_set()
                
                ttk.Label(select_dialog, text="Select a marker stream to edit:").pack(pady=10)
                
                # Listbox with streams
                stream_listbox = tk.Listbox(select_dialog, height=10)
                stream_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
                
                for _, name in marker_streams:
                    stream_listbox.insert(tk.END, f"{name}")
                
                selected_idx = [None]  # mutable reference
                
                def on_select():
                    selection = stream_listbox.curselection()
                    if selection:
                        selected_idx[0] = marker_streams[selection[0]][0]
                    select_dialog.destroy()
                    
                def on_cancel():
                    select_dialog.destroy()
                    
                # Buttons
                btn_frame = tk.Frame(select_dialog)
                btn_frame.pack(fill=tk.X, pady=10)
                ttk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=10)
                ttk.Button(btn_frame, text="Select", command=on_select).pack(side=tk.RIGHT, padx=10)
                
                # Wait for user selection
                select_dialog.wait_window()
                
                if selected_idx[0] is None:
                    return
                marker_stream_idx = selected_idx[0]
        
        # Validate stream index
        if marker_stream_idx is None or marker_stream_idx >= len(self.streams):
            messagebox.showerror("Error", "Please select a valid marker stream.")
            return
        
        # Check marker type
        marker_stream = self.streams[marker_stream_idx]
        stream_info = self.xdf_reader.get_stream_info(marker_stream)
        stype = (stream_info.get('type') or '').lower()
        if stype not in ['markers', 'marker']:
            messagebox.showerror("Error", "Selected stream is not a marker stream.")
            return
        
        # Ask user for video file
        video_path = filedialog.askopenfilename(
            title="Select video file",
            filetypes=[("Video files", "*.mp4 *.avi *.mov"), ("All files", "*.*")]
        )
        if not video_path:
            return
        
        # Prompt user to select a video frame stream (if any exist)
        video_streams = []
        for i, s in enumerate(self.streams):
            s_info = self.xdf_reader.get_stream_info(s)
            sname = (s_info.get('name') or "").lower()
            if "video" in sname or "frame" in sname:
                video_streams.append((i, s_info.get('name', f"Stream {i+1}")))
        
        video_stream = None
        selected_index = [None]  # ensure always defined
        
        if video_streams:
            dialog = tk.Toplevel(self.root)
            dialog.title("Select Video Frame Stream")
            dialog.transient(self.root)
            dialog.grab_set()
            
            tk.Label(dialog, text="Select the stream containing video frame numbers:").pack(pady=10)
            
            stream_var = tk.StringVar()
            stream_selector = ttk.Combobox(dialog, textvariable=stream_var, state="readonly")
            stream_selector['values'] = [name for _, name in video_streams]
            if stream_selector['values']:
                stream_selector.current(0)
            stream_selector.pack(pady=10, padx=20, fill=tk.X)
            
            def on_ok():
                idx = stream_selector.current()
                if idx >= 0:
                    selected_index[0] = video_streams[idx][0]
                dialog.destroy()
            
            def on_skip():
                dialog.destroy()
            
            btn_frame = ttk.Frame(dialog)
            btn_frame.pack(pady=10, fill=tk.X)
            ttk.Button(btn_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=20)
            ttk.Button(btn_frame, text="Skip (use FPS only)", command=on_skip).pack(side=tk.RIGHT, padx=20)
            
            dialog.wait_window()
            
            if selected_index[0] is not None:
                video_stream = self.streams[selected_index[0]]
        
        # Import the LSLMarkerEditor class
        try:
            from lsl_marker_editor import LSLMarkerEditor
            
            # Create offset spinbox dialog
            offset_dialog = tk.Toplevel(self.root)
            offset_dialog.title("Set Time Offset")
            offset_dialog.geometry("300x120")
            offset_dialog.transient(self.root)
            offset_dialog.grab_set()
            
            offset_var = tk.DoubleVar(value=0.0)
            offset_frame = ttk.Frame(offset_dialog, padding="10")
            offset_frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(offset_frame, text="Time offset (seconds):").pack(anchor=tk.W, pady=(0, 10))
            ttk.Spinbox(offset_frame, from_=-100, to=100, increment=0.1, textvariable=offset_var, width=10).pack(fill=tk.X)
            
            def start_editor():
                offset = offset_var.get()
                try:
                    offset_dialog.destroy()
                    
                    editor_window = tk.Toplevel(self.root)
                    editor_window.title("LSL Marker Editor")
                    editor_window.geometry("1200x800")
                    
                    # Create the marker editor with proper parent
                    marker_editor = LSLMarkerEditor(
                        parent=editor_window,
                        stream=marker_stream,
                        video_path=video_path,
                        time_offset=offset,
                        video_stream=video_stream  # may be None → FPS-only path
                    )
                    
                    editor_window.minsize(1000, 700)
                    editor_window.transient(self.root)
                    editor_window.focus_set()
                    
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to start marker editor: {e}")
                    import traceback
                    traceback.print_exc()
            
            ttk.Button(offset_dialog, text="Start Editor", command=start_editor).pack(pady=10)
            
        except ImportError as e:
            messagebox.showerror("Import Error", f"Could not import LSLMarkerEditor: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Error opening marker editor: {e}")
            import traceback
            traceback.print_exc()

    def show_about(self):
        """Show information about the application."""
        about_text = """XDF Reader Application

A tool for viewing, analyzing, and editing XDF (eXtensible Data Format) files.

Features:
- View stream data and metadata
- Export streams to CSV
- Visualize time series data
- Edit marker timestamps
- Link with video data

Version: 1.0
"""
        messagebox.showinfo("About", about_text)

    def view_stream_info(self):
        """View detailed information about the selected stream."""
        selection = self.streams_list.curselection()
        if not selection or not self.streams:
            messagebox.showinfo("No Selection", "Please select a stream to view.")
            return
        
        index = selection[0]
        if index < len(self.streams):
            stream = self.streams[index]
            stream_info = self.xdf_reader.get_stream_info(stream)
            
            # Create a detailed info dialog
            info_dialog = tk.Toplevel(self.root)
            info_dialog.title(f"Stream Info: {stream_info['name']}")
            info_dialog.geometry("600x500")
            info_dialog.transient(self.root)
            
            # Create a scrollable text area
            frame = ttk.Frame(info_dialog, padding="10")
            frame.pack(fill=tk.BOTH, expand=True)
            
            scroll = ttk.Scrollbar(frame)
            scroll.pack(side=tk.RIGHT, fill=tk.Y)
            
            info_text = tk.Text(frame, wrap=tk.WORD, yscrollcommand=scroll.set, font=("Consolas", 10))
            info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scroll.config(command=info_text.yview)
            
            # Format the info text
            info_text.insert(tk.END, f"Stream Name: {stream_info['name']}\n")
            info_text.insert(tk.END, f"Stream Type: {stream_info['type']}\n")
            info_text.insert(tk.END, f"Channel Count: {stream_info['channel_count']}\n")
            info_text.insert(tk.END, f"Nominal Sampling Rate: {stream_info['nominal_srate']}\n")
            info_text.insert(tk.END, f"Actual Sampling Rate: {stream_info['actual_srate']:.2f} Hz\n")
            info_text.insert(tk.END, f"Sample Count: {len(stream['time_stamps'])}\n\n")
            
            # Add channel info if available
            if 'channels' in stream_info and stream_info['channels']:
                info_text.insert(tk.END, "Channel Information:\n")
                for i, channel in enumerate(stream_info['channels']):
                    info_text.insert(tk.END, f"  Channel {i+1}: {channel.get('name', 'Unnamed')}\n")
                    info_text.insert(tk.END, f"    Type: {channel.get('type', 'Unknown')}\n")
                    info_text.insert(tk.END, f"    Unit: {channel.get('unit', 'Unspecified')}\n\n")
            
            # Add sample data
            info_text.insert(tk.END, "Sample Data Points:\n")
            samples = self.xdf_reader.get_sample_data(stream, max_samples=5)
            for i, sample in enumerate(samples):
                info_text.insert(tk.END, f"  Sample {i+1}:\n")
                info_text.insert(tk.END, f"    Timestamp: {sample['timestamp']}\n")
                info_text.insert(tk.END, f"    Data: {sample['data']}\n\n")
            
            # Make text read-only
            info_text.config(state=tk.DISABLED)
            
            # Close button
            ttk.Button(info_dialog, text="Close", command=info_dialog.destroy).pack(pady=10)

    def advanced_visualize(self):
        """Open advanced visualization for the selected stream."""
        selection = self.streams_list.curselection()
        if not selection or not self.streams:
            messagebox.showinfo("No Selection", "Please select a stream to visualize.")
            return
        
        index = selection[0]
        if index < len(self.streams):
            stream = self.streams[index]
            stream_info = self.xdf_reader.get_stream_info(stream)
            
            # Create a dialog for visualization
            viz_dialog = tk.Toplevel(self.root)
            viz_dialog.title(f"Advanced Visualization: {stream_info['name']}")
            viz_dialog.geometry("800x600")
            viz_dialog.transient(self.root)
            
            # Create matplotlib figure
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            import numpy as np
            
            fig, ax = plt.subplots(figsize=(8, 5))
            
            # Get the data to plot
            time_series = stream['time_series']
            time_stamps = stream['time_stamps']
            
            # Check data dimensions
            if len(time_stamps) == 0:
                tk.Label(viz_dialog, text="No data to visualize").pack(pady=20)
                return
            
            # Adjust time to start from 0
            time_offset = time_stamps[0]
            adjusted_times = [t - time_offset for t in time_stamps]
            
            # Plot based on data dimensions
            if isinstance(time_series, np.ndarray):
                if len(time_series.shape) == 1:  # 1D data
                    ax.plot(adjusted_times, time_series)
                elif time_series.shape[1] <= 10:  # 2D data with few channels
                    for i in range(time_series.shape[1]):
                        ax.plot(adjusted_times, time_series[:, i], label=f"Channel {i+1}")
                    ax.legend()
                else:  # 2D data with many channels - plot as heatmap
                    # Subsample for better visualization
                    max_points = 1000
                    if len(adjusted_times) > max_points:
                        indices = np.linspace(0, len(adjusted_times) - 1, max_points, dtype=int)
                        times_subset = [adjusted_times[i] for i in indices]
                        data_subset = time_series[indices]
                    else:
                        times_subset = adjusted_times
                        data_subset = time_series
                    
                    im = ax.imshow(data_subset.T, aspect='auto', origin='lower', 
                                 extent=[times_subset[0], times_subset[-1], 0, time_series.shape[1]])
                    fig.colorbar(im, ax=ax, label='Amplitude')
                    ax.set_ylabel('Channel')
            else:
                # Handle non-numpy data
                ax.plot(adjusted_times, time_series)
            
            ax.set_xlabel('Time (s)')
            ax.set_title(f"{stream_info['name']} - {stream_info['type']}")
            
            # Create canvas
            canvas = FigureCanvasTkAgg(fig, master=viz_dialog)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Add toolbar
            from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
            toolbar_frame = tk.Frame(viz_dialog)
            toolbar_frame.pack(fill=tk.X)
            NavigationToolbar2Tk(canvas, toolbar_frame)
            
            # Close button
            ttk.Button(viz_dialog, text="Close", command=viz_dialog.destroy).pack(pady=10)

def main():
    root = tk.Tk()
    app = XDFApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()

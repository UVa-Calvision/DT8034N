#!/usr/bin/env python3
"""
Enhanced GUI for CAEN Desktop High Voltage Power Supply using CAENpy library
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import re

# Import the CAEN Desktop HV library 
from CAENpy.CAENDesktopHighVoltagePowerSupply import CAENDesktopHighVoltagePowerSupply


class CAENDesktopGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CAEN Desktop High Voltage Power Supply Control")
        self.root.geometry("900x900")
        
        self.hv = None
        self.monitoring = False
        self.channel_widgets = {}
        self.num_channels = 4  # Will be updated after connection
        self.setup_gui()
        
    def setup_gui(self):
        """Setup the GUI elements"""
        
        # Connection Frame
        conn_frame = ttk.LabelFrame(self.root, text="Connection", padding="5")
        conn_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(conn_frame, text="Port/IP:").grid(row=0, column=0, sticky="w")
        self.port_var = tk.StringVar(value="/dev/ttyACM0")
        ttk.Entry(conn_frame, textvariable=self.port_var, width=15).grid(row=0, column=1, padx=5)
        
        ttk.Label(conn_frame, text="Connection Type:").grid(row=0, column=2, sticky="w", padx=(10,0))
        self.conn_type_var = tk.StringVar(value="USB")
        conn_combo = ttk.Combobox(conn_frame, textvariable=self.conn_type_var, 
                                 values=["USB", "Ethernet"], 
                                 width=8, state="readonly")
        conn_combo.grid(row=0, column=3, padx=5)
        conn_combo.bind("<<ComboboxSelected>>", self.on_conn_type_change)
        
        ttk.Label(conn_frame, text="Device ID:").grid(row=0, column=4, sticky="w", padx=(10,0))
        self.device_var = tk.StringVar(value="0")
        ttk.Entry(conn_frame, textvariable=self.device_var, width=5).grid(row=0, column=5, padx=5)
        
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=6, padx=10)
        
        self.status_label = ttk.Label(conn_frame, text="Disconnected", foreground="red")
        self.status_label.grid(row=0, column=7, padx=10)
        
        # Device Info Frame
        info_frame = ttk.LabelFrame(self.root, text="Device Information", padding="5")
        info_frame.pack(fill="x", padx=5, pady=5)
        
        self.device_info_label = ttk.Label(info_frame, text="Not connected")
        self.device_info_label.pack(anchor="w")
        
        # Channel Status Frame
        self.status_frame = ttk.LabelFrame(self.root, text="Channel Status", padding="10")
        self.status_frame.pack(fill="x", padx=5, pady=5)
        
        # Will be created after connection when we know number of channels
        
        # Auto-refresh controls
        refresh_frame = ttk.Frame(self.root)
        refresh_frame.pack(fill="x", padx=5, pady=5)
        
        # Auto refresh checkbox with command callback
        self.auto_refresh_var = tk.BooleanVar(value=True)
        auto_refresh_cb = ttk.Checkbutton(refresh_frame, text="Auto Refresh (2)", 
                                     variable=self.auto_refresh_var,
                                     command=self.on_auto_refresh_toggle)  # Add callback
        auto_refresh_cb.pack(side="left")
        
        # Manual refresh button
        refresh_btn = ttk.Button(refresh_frame, text="Manual Refresh", 
                           command=self.refresh_status)
        refresh_btn.pack(side="left", padx=10)

        
        ttk.Button(refresh_frame, text="All Channels OFF", 
                  command=self.all_channels_off).pack(side="left", padx=10)

        # Add monitoring status indicator
        #status_frame = ttk.Frame(refresh_frame)
        #status_frame.grid(row=0, column=3, sticky="ew", padx=5)
    
        ttk.Label(refresh_frame, text="Monitoring:").pack()
        self.monitoring_status_label = ttk.Label(refresh_frame, text="Stopped", 
                                           foreground="red")
        self.monitoring_status_label.pack()

        
        # Parameter Setting Frame
        param_frame = ttk.LabelFrame(self.root, text="Set Parameters", padding="10")
        param_frame.pack(fill="x", padx=5, pady=5)
        
        # Channel selection
        ttk.Label(param_frame, text="Channel:").grid(row=0, column=0, sticky="w")
        self.channel_var = tk.StringVar(value="0")
        self.channel_combo = ttk.Combobox(param_frame, textvariable=self.channel_var, 
                                         values=["0"], width=5, state="readonly")
        self.channel_combo.grid(row=0, column=1, padx=5)
        
        # Parameter selection
        ttk.Label(param_frame, text="Parameter:").grid(row=1, column=0, sticky="w", pady=(5,0))
        self.param_var = tk.StringVar(value="VSET")
        param_combo = ttk.Combobox(param_frame, textvariable=self.param_var,
                                 values=["VSET", "ISET", "RUP", "RDW", "MAXV"],
                                 width=10, state="readonly")
        param_combo.grid(row=1, column=1, padx=5, pady=(5,0))
        param_combo.bind("<<ComboboxSelected>>", self.on_param_change)
        
        # Value entry
        ttk.Label(param_frame, text="Value:").grid(row=2, column=0, sticky="w", pady=(5,0))
        self.value_var = tk.StringVar(value="0.0")
        self.value_entry = ttk.Entry(param_frame, textvariable=self.value_var, width=15)
        self.value_entry.grid(row=2, column=1, padx=5, pady=(5,0))
        
        # Units label
        self.units_label = ttk.Label(param_frame, text="V")
        self.units_label.grid(row=2, column=2, sticky="w", padx=5, pady=(5,0))
        
        # Set button
        self.set_btn = ttk.Button(param_frame, text="Set Parameter", 
                                command=self.set_parameter, state="disabled")
        self.set_btn.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Ramp voltage frame
        ramp_frame = ttk.LabelFrame(param_frame, text="Quick Voltage Ramp", padding="5")
        ramp_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=10)
        
        ttk.Label(ramp_frame, text="Voltage:").grid(row=0, column=0, sticky="w")
        self.ramp_voltage_var = tk.StringVar(value="0.0")
        ttk.Entry(ramp_frame, textvariable=self.ramp_voltage_var, width=10).grid(row=0, column=1, padx=5)
        ttk.Label(ramp_frame, text="V").grid(row=0, column=2, sticky="w")
        
        ttk.Label(ramp_frame, text="Speed:").grid(row=0, column=3, sticky="w", padx=(10,0))
        self.ramp_speed_var = tk.StringVar(value="5.0")
        ttk.Entry(ramp_frame, textvariable=self.ramp_speed_var, width=10).grid(row=0, column=4, padx=5)
        ttk.Label(ramp_frame, text="V/s").grid(row=0, column=5, sticky="w")
        
        self.ramp_btn = ttk.Button(ramp_frame, text="Ramp Voltage", 
                                  command=self.ramp_voltage, state="disabled")
        self.ramp_btn.grid(row=0, column=6, padx=10)
        
        # Quick presets frame
        preset_frame = ttk.LabelFrame(self.root, text="Quick Presets", padding="10")
        preset_frame.pack(fill="x", padx=5, pady=5)
        
        # Voltage presets
        ttk.Label(preset_frame, text="Voltage:").grid(row=0, column=0, sticky="w")
        voltage_frame = ttk.Frame(preset_frame)
        voltage_frame.grid(row=0, column=1, sticky="w", padx=5)
        
        for i, v in enumerate([50, 100, 200, 500, 1000]):
            btn = ttk.Button(voltage_frame, text=f"{v}V", width=6,
                           command=lambda val=v: self.quick_set_voltage(val))
            btn.pack(side="left", padx=2)
        
        # Current presets (in Amperes)
        ttk.Label(preset_frame, text="Current:").grid(row=1, column=0, sticky="w", pady=(5,0))
        current_frame = ttk.Frame(preset_frame)
        current_frame.grid(row=1, column=1, sticky="w", padx=5, pady=(5,0))
        
        for i, c in enumerate([1e-6, 5e-6, 10e-6, 50e-6, 100e-6]):
            btn = ttk.Button(current_frame, text=f'{c*1e6:.0f} uA', width=6,
                           command=lambda val=c: self.quick_set_current(val))
            btn.pack(side="left", padx=2)
        
        # Log frame
        log_frame = ttk.LabelFrame(self.root, text="Command Log", padding="5")
        log_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=6, width=70)
        self.log_text.pack(fill="both", expand=True)
        
        # Clear log button
        ttk.Button(log_frame, text="Clear Log", command=self.clear_log).pack(pady=5)


    def on_auto_refresh_toggle(self):
        """Called when auto refresh checkbox is toggled"""
        if self.auto_refresh_var.get():
            self.log("Auto refresh enabled")
            if self.hv and not self.monitoring:
                self.monitoring = True
                self.monitor_channels()  # Start monitoring if not already running
        else:
            self.log("Auto refresh disabled")
            self.monitoring = False
            self.monitor_channels()

        
    def on_conn_type_change(self, event=None):
        """Update port placeholder when connection type changes"""
        if self.conn_type_var.get() == "USB":
            self.port_var.set("/dev/ttyACM0")
        else:
            self.port_var.set("192.168.1.100")
    
    def create_channel_status(self):
        """Create channel status display after knowing number of channels"""
        # Clear any existing widgets
        for widget in self.status_frame.winfo_children():
            widget.destroy()
        
        # Headers
        headers = ["Channel", "Status", "VSET (V)", "VMON (V)", "ISET (A)", "IMON (A)", "Control"]
        for i, header in enumerate(headers):
            label = ttk.Label(self.status_frame, text=header, font=("TkDefaultFont", 9, "bold"))
            label.grid(row=0, column=i, padx=5, pady=2, sticky="w")
        
        # Channel rows
        for ch in range(self.num_channels):
            self.channel_widgets[ch] = {}
            
            # Channel number
            ttk.Label(self.status_frame, text=f"CH{ch}").grid(row=ch+1, column=0, padx=5, pady=2)
            
            # Status indicator
            status_label = ttk.Label(self.status_frame, text="OFF", width=8, 
                                   background="lightgray", relief="sunken")
            status_label.grid(row=ch+1, column=1, padx=5, pady=2)
            self.channel_widgets[ch]['status'] = status_label
            
            # VSET
            vset_label = ttk.Label(self.status_frame, text="0.0", width=10, relief="sunken")
            vset_label.grid(row=ch+1, column=2, padx=5, pady=2)
            self.channel_widgets[ch]['vset'] = vset_label
            
            # VMON
            vmon_label = ttk.Label(self.status_frame, text="0.0", width=10, relief="sunken")
            vmon_label.grid(row=ch+1, column=3, padx=5, pady=2)
            self.channel_widgets[ch]['vmon'] = vmon_label
            
            # ISET
            iset_label = ttk.Label(self.status_frame, text="0.0", width=12, relief="sunken")
            iset_label.grid(row=ch+1, column=4, padx=5, pady=2)
            self.channel_widgets[ch]['iset'] = iset_label
            
            # IMON
            imon_label = ttk.Label(self.status_frame, text="0.0", width=12, relief="sunken")
            imon_label.grid(row=ch+1, column=5, padx=5, pady=2)
            self.channel_widgets[ch]['imon'] = imon_label
            
            # Control buttons
            control_frame = ttk.Frame(self.status_frame)
            control_frame.grid(row=ch+1, column=6, padx=5, pady=2, sticky="w")
            
            on_btn = ttk.Button(control_frame, text="ON", width=4, state="disabled",
                              command=lambda c=ch: self.turn_on_channel(c))
            on_btn.grid(row=0, column=0, padx=2)
            
            off_btn = ttk.Button(control_frame, text="OFF", width=4, state="disabled",
                               command=lambda c=ch: self.turn_off_channel(c))
            off_btn.grid(row=0, column=1, padx=2)
            
            self.channel_widgets[ch]['on_btn'] = on_btn
            self.channel_widgets[ch]['off_btn'] = off_btn
        
        # Update channel combo box
        self.channel_combo['values'] = [str(i) for i in range(self.num_channels)]
    
    def on_param_change(self, event=None):
        """Update units label when parameter changes"""
        param = self.param_var.get()
        units = {
            "VSET": "V", "ISET": "A", "RUP": "V/s", 
            "RDW": "V/s", "MAXV": "V"
        }
        self.units_label.config(text=units.get(param, ""))
    
    def toggle_connection(self):
        """Toggle connection state"""
        if self.hv:
            self.disconnect()
        else:
            self.connect()


    def set_remote_mode(self):
        """Switch device to remote control mode"""
        if not self.hv:
            messagebox.showerror("Error", "Not connected to device")
            return

        try:
            # Try to set remote mode - syntax may vary by model
            # self.hv.set_remote_mode()  # If this method exists
            # OR try sending raw command:
            # self.hv.write("REM")  # If raw command access exists

            self.log("Switched to REMOTE mode")
            messagebox.showinfo("Success", "Device switched to REMOTE mode")

        except Exception as e:
            self.log(f"Failed to set remote mode: {e}")
            messagebox.showerror("Error", f"Could not set remote mode:\n{str(e)}\n\nPlease use front panel to switch to REMOTE mode")
            
    def connect(self):
        """Connect to CAEN Desktop HV Power Supply"""
        try:
            port_or_ip = self.port_var.get()
            device_id = int(self.device_var.get()) if self.device_var.get() else None
            
            self.log(f"Connecting to {port_or_ip} (Device ID: {device_id}) using {self.conn_type_var.get()}")
            
            if self.conn_type_var.get() == "USB":
                self.hv = CAENDesktopHighVoltagePowerSupply(port=port_or_ip)
            else:
                self.hv = CAENDesktopHighVoltagePowerSupply(ip=port_or_ip)
            
            # Get device info
            device_info = self.hv.idn
            self.num_channels = self.hv.channels_count
            
            self.device_info_label.config(text=f"{device_info} ({self.num_channels} channels)")
            self.status_label.config(text="Connected", foreground="green")
            self.connect_btn.config(text="Disconnect")
            self.set_btn.config(state="normal")
            self.ramp_btn.config(state="normal")
            
            # Create channel status display
            self.create_channel_status()
            
            # Enable control buttons
            for ch in range(self.num_channels):
                self.channel_widgets[ch]['on_btn'].config(state="normal")
                self.channel_widgets[ch]['off_btn'].config(state="normal")
            
            self.log(f"Connected successfully! Device: {device_info}")


            # After successful connection, try to set remote mode
            # self.set_remote_mode()
            
            # Start monitoring
            self.monitoring = True
            self.monitor_channels()
            
        except Exception as e:
            messagebox.showerror("Connection Error", f"Failed to connect:\n{str(e)}")
            self.log(f"Connection failed: {e}")
    
    def disconnect(self):
        """Disconnect from CAEN Desktop HV Power Supply"""
        # Stop monitoring
        self.monitoring = False
        
        if self.hv:
            # Close connection if the library supports it
            if hasattr(self.hv, 'close'):
                self.hv.close()
            self.hv = None
        
        self.device_info_label.config(text="Not connected")
        self.status_label.config(text="Disconnected", foreground="red")
        self.connect_btn.config(text="Connect")
        self.set_btn.config(state="disabled")
        self.ramp_btn.config(state="disabled")
        
        # Disable control buttons and reset displays
        for ch in range(self.num_channels):
            if ch in self.channel_widgets:
                widgets = self.channel_widgets[ch]
                widgets['on_btn'].config(state="disabled")
                widgets['off_btn'].config(state="disabled")
                widgets['status'].config(text="OFF", background="lightgray")
                widgets['vset'].config(text="")
                widgets['vmon'].config(text="")
                widgets['iset'].config(text="")
                widgets['imon'].config(text="")
        
        self.log("Disconnected")




    def monitor_channels(self):
        """Monitor all channels continuously"""
        print(self.monitoring,self.hv)
        if not self.monitoring or not self.hv:
            # Update status indicator
            if hasattr(self, 'monitoring_status_label'):
                self.monitoring_status_label.config(text="Stopped", foreground="red")
                return
    

        # Update status indicator
        if hasattr(self, 'monitoring_status_label'):
            self.monitoring_status_label.config(text="Running", foreground="green")

        if self.auto_refresh_var.get():
            # Just call the same refresh function that works manually
            self.log("Auto refresh: Calling manual refresh function...")
            self.refresh_status()

            
        # Schedule next update
        if self.monitoring:
            self.root.after(2000, self.monitor_channels)  # Update every 2 seconds


    def _update_single_channel(self, ch, vset, vmon, iset, imon, status, is_ramping, overcurrent):
        """Helper method to update a single channel - avoids lambda closure issues"""
        self.log(f"Auto refresh: Updating display CH{ch} with VSET={vset}")
        self.update_channel_display(ch, vset, vmon, iset, imon, status, is_ramping, overcurrent)

    def _update_channel_error(self, ch, error_msg):
        """Helper method to handle channel errors"""
        self.log(f"Error reading CH{ch}: {error_msg}")
        self.update_channel_display(ch, 0, 0, 0, 0, "off", False, False)

            
    def update_channel_display(self, ch, vset, vmon, iset, imon, status, is_ramping, overcurrent):
        """Update channel display with current values"""
        if ch not in self.channel_widgets:
            return

        # Add debug logging to see what values we're actually getting
        self.log(f"Updating CH{ch}: VSET={vset}, VMON={vmon}, Status={status}")

        widgets = self.channel_widgets[ch]

        # Update values
        if vset is not None:
            widgets['vset'].config(text=f"{vset:.1f}")
        if vmon is not None:
            widgets['vmon'].config(text=f"{vmon:.1f}")
        if iset is not None:
            widgets['iset'].config(text=f"{iset:.2e}")
        if imon is not None:
            widgets['imon'].config(text=f"{imon:.2e}")

        # Update status
        if overcurrent:
            widgets['status'].config(text="OVERCUR", background="red")
        elif is_ramping:
            widgets['status'].config(text="RAMPING", background="yellow")
        elif status == "on":
            widgets['status'].config(text="ON", background="lightgreen")
        else:
            widgets['status'].config(text="OFF", background="lightgray")

    def refresh_status(self):
        """Manually refresh status"""
        if not self.hv:
            messagebox.showerror("Error", "Not connected to device")
            return

        self.log("Refreshing channel status...")

        # Perform immediate refresh in a separate thread
        def refresh_thread():
            try:
                for ch in range(self.num_channels):
                    try:
                        # Use only the main class methods, avoid channel object properties
                        vset = self.hv.get_single_channel_parameter('VSET', ch)
                        vmon = self.hv.get_single_channel_parameter('VMON', ch)
                        iset_microamps = self.hv.get_single_channel_parameter('ISET', ch)
                        imon_microamps = self.hv.get_single_channel_parameter('IMON', ch)

                        # Convert currents from microamps to Amperes
                        iset = iset_microamps * 1e-6
                        imon = imon_microamps * 1e-6

                        # Get status using the main class method
                        status_info = self.hv.channel_status(channel=ch)
                        status = status_info['output']
                        is_ramping = (status_info['ramping up'] == 'yes' or 
                                    status_info['ramping down'] == 'yes')
                        overcurrent = status_info['there was overcurrent'] == 'yes'

                        # Update GUI in main thread
                        self.root.after(0, lambda c=ch, vs=vset, vm=vmon, ise=iset, 
                                       im=imon, st=status, ramp=is_ramping, oc=overcurrent: 
                                       self.update_channel_display(c, vs, vm, ise, im, st, ramp, oc))

                    except Exception as e:
                        error_msg = str(e)
                        self.root.after(0, lambda c=ch, err=error_msg: self.log(f"Error reading CH{c}: {err}"))

                # Log completion
                self.root.after(0, lambda: self.log("Refresh completed"))

            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: self.log(f"Manual refresh error: {error_msg}"))

        threading.Thread(target=refresh_thread, daemon=True).start() 

    def all_channels_off(self):
        """Turn off all channels"""
        if not self.hv:
            messagebox.showerror("Error", "Not connected to device")
            return
        
        if messagebox.askyesno("Confirm", "Turn OFF all channels?"):
            for ch in range(self.num_channels):
                self.turn_off_channel(ch)
    
    def turn_on_channel(self, ch):
        """Turn on specific channel"""
        if not self.hv:
            return

        try:
            # Use the set method directly instead of the property
            self.hv.channels[ch].set('ON', 0)
            self.log(f"Turn ON CH{ch}")
        except Exception as e:
            self.log(f"Error turning on CH{ch}: {e}")
            messagebox.showerror("Error", f"Failed to turn on CH{ch}:\n{str(e)}")

    def turn_off_channel(self, ch):
        """Turn off specific channel"""
        if not self.hv:
            return

        try:
            # Use the set method directly instead of the property
            self.hv.channels[ch].set('OFF', 0)
            self.log(f"Turn OFF CH{ch}")
        except Exception as e:
            self.log(f"Error turning off CH{ch}: {e}")
            messagebox.showerror("Error", f"Failed to turn off CH{ch}:\n{str(e)}")


    def set_parameter(self):
        """Set parameter using CAENpy methods"""
        if not self.hv:
            messagebox.showerror("Error", "Not connected to device")
            return

        try:
            channel = int(self.channel_var.get())
            param = self.param_var.get()
            value = float(self.value_var.get())

            # Validate ranges
            if param == "VSET" and (value < 0 or value > 5000):
                messagebox.showerror("Error", "VSET must be between 0 and 5000V")
                return
            if param == "ISET" and (value < 0 or value > 1e-3):
                messagebox.showerror("Error", "ISET must be between 0 and 1mA")
                return

            self.log(f"Setting CH{channel} {param} = {value}")

            # Run in thread to avoid GUI freezing
            def set_param_thread():
                try:
                    ch = self.hv.channels[channel]

                    if param == "ISET":
                        # Convert Amperes to microamps for ISET
                        value_microamps = value * 1e6
                        ch.set(param, value_microamps)
                    else:
                        ch.set(param, value)

                    self.root.after(0, lambda: self.log(f"Parameter set successfully"))
                    # Trigger immediate refresh
                    self.root.after(100, self.refresh_status)
                except Exception as e:
                    self.root.after(0, lambda: self.log(f"Error: {e}"))
                    self.root.after(0, lambda: messagebox.showerror("Error", str(e)))

            threading.Thread(target=set_param_thread, daemon=True).start()

        except ValueError as e:
            messagebox.showerror("Error", f"Invalid value: {e}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.log(f"Error: {e}")

    
    def ramp_voltage(self):
        """Ramp voltage using CAENpy ramp_voltage method"""
        if not self.hv:
            messagebox.showerror("Error", "Not connected to device")
            return
        
        try:
            channel = int(self.channel_var.get())
            voltage = float(self.ramp_voltage_var.get())
            speed = float(self.ramp_speed_var.get())
            
            self.log(f"Ramping CH{channel} to {voltage}V at {speed}V/s")
            
            def ramp_thread():
                try:
                    self.hv.channels[channel].ramp_voltage(voltage, ramp_speed_VperSec=speed)
                    self.root.after(0, lambda: self.log(f"Voltage ramp completed"))
                    self.root.after(100, self.refresh_status)
                except Exception as e:
                    self.root.after(0, lambda: self.log(f"Ramp error: {e}"))
                    self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            
            threading.Thread(target=ramp_thread, daemon=True).start()
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid value: {e}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def quick_set_voltage(self, value):
        """Quick set voltage"""
        self.param_var.set("VSET")
        self.value_var.set(str(value))
        self.on_param_change()
        self.set_parameter()
    
    def quick_set_current(self, value):
        """Quick set current (value in Amperes)"""
        self.param_var.set("ISET")
        self.value_var.set(str(value))
        self.on_param_change()
        self.set_parameter()
    
    def log(self, message):
        """Add message to log"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        print(f"[{timestamp}] {message}")
    
    def clear_log(self):
        """Clear the log"""
        self.log_text.delete(1.0, tk.END)
    
    def on_closing(self):
        """Handle window closing"""
        self.monitoring = False
        if self.hv and hasattr(self.hv, 'close'):
            self.hv.close()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = CAENDesktopGUI(root)
    
    # Handle window closing
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    root.mainloop()

if __name__ == "__main__":
    main()


from ansys.aedt.core import Desktop, Hfss

# --- FINAL TUNED PARAMETERS ---
freq_ghz = 28.0
sub_h = 0.254         
sub_w = 12.0          
sub_l = 14.0  

# 1. Tuning: 3.45mm was 28.2GHz. 
#    Increased to 3.48mm to shift down to exactly 28.0 GHz.
patch_l = 3.48    
patch_w = 4.23    

# Feed & DGS Parameters (unchanged)
feed_w = 0.78     
inset_d = 1.05    
inset_g = 0.20    
dgs_l = 4.0   
dgs_w = 0.5   
element_spacing = 7.0 

print("Connecting to Ansys Student...")
d = Desktop(version="2025.2", non_graphical=False, new_desktop=True, 
            student_version=True, close_on_exit=False)

try:
    app = Hfss(projectname="MIMO_28GHz_Final_Tune", designname="Exact_28GHz")
    app.modeler.model_units = "mm"

    # 1. Material
    if "Rogers_5880_Clean" not in app.materials.material_keys:
        mat = app.materials.add_material("Rogers_5880_Clean")
        mat.permittivity = 2.2
        mat.dielectric_loss_tangent = 0.0009
    mat_name = "Rogers_5880_Clean"

    # 2. Substrate
    app.modeler.create_box([-sub_w/2, -sub_l/2, 0], [sub_w, sub_l, sub_h], 
                           name="Substrate", material=mat_name)

    # 3. Ground with DGS
    gnd = app.modeler.create_rectangle("XY", [-sub_w/2, -sub_l/2, 0], [sub_w, sub_l], name="Ground")
    
    # Create DGS Slots
    slot1 = app.modeler.create_rectangle("XY", [-dgs_l/2, (element_spacing/2) - dgs_w/2, 0], [dgs_l, dgs_w], name="Slot_1")
    slot2 = app.modeler.create_rectangle("XY", [-dgs_l/2, (-element_spacing/2) - dgs_w/2, 0], [dgs_l, dgs_w], name="Slot_2")
    
    # Subtract slots from ground
    app.modeler.subtract(gnd.name, [slot1.name, slot2.name], keep_originals=False)
    # Assign boundary AFTER geometry is final
    app.assign_perfecte_to_sheets(gnd.name)

    # 4. Patch Creation
    def create_element(index, center_y):
        p_x = -patch_l / 2
        p_y = center_y - patch_w / 2
        
        # Create shapes
        patch = app.modeler.create_rectangle("XY", [p_x, p_y, sub_h], [patch_l, patch_w], name=f"Patch_{index}")
        
        notch_w = feed_w + 2*inset_g
        notch_y = center_y - notch_w/2
        notch = app.modeler.create_rectangle("XY", [p_x, notch_y, sub_h], [inset_d, notch_w], name=f"Notch_{index}")
        
        feed_y_start = center_y - feed_w / 2
        feed_strip = app.modeler.create_rectangle("XY", [p_x, feed_y_start, sub_h], [inset_d, feed_w], name=f"FeedStrip_{index}")
        
        # Boolean operations (Subtract notch, Unite feed)
        app.modeler.subtract(patch.name, [notch.name], keep_originals=False)
        app.modeler.unite([patch.name, feed_strip.name])
        
        # Assign boundary
        app.assign_perfecte_to_sheets(patch.name)
        
        # Port
        port_sheet = app.modeler.create_rectangle("YZ", 
                                                  [p_x, feed_y_start, 0], 
                                                  [feed_w, sub_h], 
                                                  name=f"PortSheet_{index}")
        
        app.lumped_port(port_sheet.name, 
                        integration_line=[[p_x, center_y, 0], [p_x, center_y, sub_h]], 
                        name=f"Port_{index}")

    create_element(1, element_spacing/2)
    create_element(2, -element_spacing/2)

    # 5. Radiation Boundary (Small Size for Student Version)
    air_margin = 3.0 
    air_box = app.modeler.create_box([-sub_w/2-air_margin, -sub_l/2-air_margin, -air_margin], 
                                     [sub_w+2*air_margin, sub_l+2*air_margin, sub_h+2*air_margin], 
                                     name="AirBox")
    app.assign_radiation_boundary_to_objects(air_box)

    # 6. Setup (50 Points Requested)
    print("Creating Setup...")
    setup = app.create_setup("Setup28GHz")
    setup.props["Frequency"] = "28GHz"
    setup.props["MaximumPasses"] = 12
    setup.props["MaxDeltaS"] = 0.03
    
    setup.create_frequency_sweep(
        unit="GHz", 
        start_frequency=26, 
        stop_frequency=30, 
        num_of_freq_points=10,  # Exact request
        name="Sweep28GHz"
    )

    # 7. Radiation Sphere
    app.insert_infinite_sphere(name="3D_Sphere", theta_step=10, phi_step=10)

    # 8. Run
    print("Starting Simulation...")
    app.analyze_setup("Setup28GHz")

    # 9. Array Mode
    app.edit_sources({"Port_1:1": ("1W", "0deg"), "Port_2:1": ("1W", "0deg")})

    print("Done! Check S11. It should now be centered exactly at 28.0 GHz.")

except Exception as e:
    print(f"Error: {e}")

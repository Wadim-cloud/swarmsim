// High-Fidelity Turntable
// Enhanced and fully parameterized 

include <BOSL2/std.scad>
include <BOSL2/rounding.scad>
include <BOSL2/beziers.scad>

/* [Playback & Animation] */
// Rotate the tonearm over the record (0 = resting, 25 = playing)
tonearm_angle = 15;        // [0:1:35]
// Rotate the platter for animation
platter_spin_angle = 0;    // [0:1:360]
// Display the vinyl record
show_record = true;        // 
// Show the acrylic dust cover
show_dust_cover = false;   // 

/* [Dimensions] */
base_width = 46;           // [30:1:60]
base_depth = 36;           // [25:1:50]
base_height = 4;           // [2:0.5:8]
platter_radius = 16.5;     // [10:0.5:25]
platter_height = 2.5;      // [1:0.5:5]
record_radius = 15;      // [10:0.5:20]

/* [Colors] */
color_base = "#242426";
color_base_plateau = "#18181A";
color_platter = "#4A4A50";
color_rim_dots = "#666670";
color_record = "#0F0F0F";
color_label = "#D43535";
color_metal = "#B0B0B5";
color_tonearm = "#D0D0D5";
color_stylus = "#D4AF37";
color_buttons = "#888890";
color_dust_cover = "#E0E8F033"; // with transparency

/* [Resolution] */
$fn = 64;

// Central coordinates derived from base dimensions
spindle_pos = [-6, 2, 0];
pivot_pos = [14, -12, 0];

module turntable_base() {
    // Main deck
    color(color_base)
    down(base_height/2)
    cuboid([base_width, base_depth, base_height], rounding=1.5, edges="Z");
    
    // Subtle raised plateau for the platter area
    color(color_base_plateau)
    move([spindle_pos[0], spindle_pos[1], 0])
    cyl(r=platter_radius + 2, h=0.2, anchor=BOTTOM);
    
    // Feet
    color(color_record)
    for (x = [-base_width/2 + 4, base_width/2 - 4]) {
        for (y = [-base_depth/2 + 4, base_depth/2 - 4]) {
            move([x, y, -base_height/2])
            cyl(r=3.5, h=2, chamfer=0.5, anchor=TOP);
        }
    }
    
    // Power dial / Strobe tower (bottom left)
    color(color_metal)
    move([-base_width/2 + 4, -base_depth/2 + 4, 0]) {
        cyl(r=2, h=1.5, anchor=BOTTOM);
        up(1.5) cyl(r=1.2, h=1, chamfer=0.2, anchor=BOTTOM);
        // Strobe light cone
        move([1.5, 1.5, 1]) yrot(45) cyl(r=0.3, h=1, anchor=BOTTOM);
    }
    
    // Start / Stop Button
    color(color_buttons)
    move([-base_width/2 + 10, -base_depth/2 + 4, 0])
    cuboid([4, 2.5, 0.6], rounding=0.4, edges="Z", anchor=BOTTOM);
    
    // Speed Buttons (33 / 45)
    color(color_buttons) {
        move([-base_width/2 + 15, -base_depth/2 + 4, 0])
        cuboid([2, 1.5, 0.4], rounding=0.2, edges="Z", anchor=BOTTOM);
        
        move([-base_width/2 + 18, -base_depth/2 + 4, 0])
        cuboid([2, 1.5, 0.4], rounding=0.2, edges="Z", anchor=BOTTOM);
    }
    
    // Pitch Fader
    move([base_width/2 - 5, -base_depth/2 + 10, 0]) {
        // Slot
        color(color_base_plateau)
        down(0.1) cuboid([1.5, 12, 0.3], rounding=0.5, edges="Z", anchor=BOTTOM);
        
        // Fader Knob
        color(color_metal)
        move([0, -2, 0])
        cuboid([3, 1.5, 1.2], rounding=0.2, edges="Z", anchor=BOTTOM);
    }
    
    // 45 RPM Adapter (Top Left)
    color(color_metal)
    move([-base_width/2 + 5, base_depth/2 - 5, 0])
    cyl(r=1.8, h=1.5, chamfer=0.3, anchor=BOTTOM);
    
    // Tonearm Rest
    color(color_base_plateau)
    move([pivot_pos[0] - 1.5, pivot_pos[1] + 16, 0]) {
        cyl(r=2, h=1, anchor=BOTTOM);
        color(color_metal)
        up(1) cyl(r=0.6, h=platter_height + 0.5, anchor=BOTTOM);
        color(color_record)
        up(platter_height + 1.5) cuboid([2, 1, 1], anchor=BOTTOM);
    }
}

module spinning_platter() {
    move(spindle_pos) {
        zrot(platter_spin_angle) {
            // Platter with strobe dots
            color(color_platter)
            difference() {
                cyl(r=platter_radius, h=platter_height, chamfer=0.2, anchor=BOTTOM);
                
                // Strobe dot cuts (creates iconic scalloped edge)
                for(i=[0 : 2 : 119]) {
                    zrot(i * 3)
                    right(platter_radius)
                    cyl(r=0.25, h=platter_height + 1, anchor=CENTER);
                }
            }
            
            if (show_record) {
                up(platter_height)
                vinyl_record();
            }
        }
        
        // Spindle (does not spin with platter in this model context, though physically it usually does)
        color(color_metal)
        cyl(r=0.4, h=platter_height + 2.5, anchor=BOTTOM);
    }
}

module vinyl_record() {
    color(color_record)
    difference() {
        cyl(r=record_radius, h=0.8, chamfer=0.1, anchor=BOTTOM);
        
        // Grooves (subtle indented rings)
        for (r = [5.5 : 0.8 : record_radius - 1]) {
            tube(ir=r, or=r+0.15, h=2, anchor=BOTTOM);
        }
    }
    
    // Record Label
    color(color_label)
    up(0.8)
    cyl(r=4.5, h=0.05, anchor=BOTTOM);
}

module tonearm_assembly() {
    move(pivot_pos) {
        // Pivot Base
        color(color_metal)
        cyl(r=3.5, h=platter_height - 0.5, chamfer=0.5, anchor=BOTTOM);
        
        up(platter_height - 0.5) {
            // Gimbal Ring
            color(color_tonearm)
            difference() {
                cuboid([4.5, 4.5, 3.5], rounding=0.5, anchor=BOTTOM);
                cuboid([3, 5.5, 2.5], anchor=BOTTOM);
            }
            
            // Rotating Arm Assembly
            up(1.75) zrot(tonearm_angle) {
                
                // Center Pivot Joint
                color(color_metal)
                cyl(r=1.2, h=3, orient=RIGHT, anchor=CENTER);
                
                // Counterweight Assembly (Negative Y direction)
                color(color_metal) {
                    // Back tube
                    xrot(90) cyl(r=0.5, h=5, anchor=BOTTOM);
                    // Weight
                    back(3.5) xrot(90) cyl(r=1.6, h=2.5, chamfer=0.2, anchor=CENTER);
                    // Anti-skate dial hint
                    move([2.5, -1, -0.5]) cyl(r=0.8, h=0.5, orient=RIGHT, anchor=BOTTOM);
                }
                
                // S-Shaped Arm Tube (Positive Y direction)
                color(color_tonearm) {
                    // Define S-curve for the tonearm
                    arm_pts = [
                        [0, 0, 0], 
                        [3, 8, 0], 
                        [-4, 16, 0], 
                        [-1, 23.5, 0]
                    ];
                    bpath = bezpath_curve(arm_pts, splinesteps=32);
                    path_sweep(circle(r=0.35), bpath);
                }
                
                // Headshell and Cartridge
                // Placed at the end of the S-curve
                translate([-1, 23.5, 0]) 
                zrot(24) { // Offset angle to align with record grooves
                    
                    // Collar
                    color(color_metal)
                    xrot(90) cyl(r=0.55, h=1.5, anchor=BOTTOM);
                    
                    // Headshell Body
                    color(color_base_plateau)
                    move([0, 1.5, 0])
                    cuboid([2.5, 4.5, 0.8], rounding=0.2, edges="Z", anchor=BOTTOM);
                    
                    // Finger Lift
                    color(color_metal)
                    move([1.2, 2.5, 0.4])
                    cuboid([1.5, 0.4, 0.2], anchor=LEFT);
                    
                    // Cartridge & Stylus
                    color(color_stylus)
                    move([0, 2.8, -0.1])
                    cuboid([1.8, 3, 1.5], chamfer=0.2, anchor=TOP);
                    
                    // Needle hint
                    color(color_record)
                    move([0, 3.5, -1.6])
                    cyl(r=0.1, h=0.6, anchor=TOP);
                }
            }
        }
    }
}

module dust_cover() {
    if (show_dust_cover) {
        color(color_dust_cover)
        up(0.1)
        difference() {
            cuboid([base_width - 1, base_depth - 1, 12], rounding=1, edges="Z", anchor=BOTTOM);
            down(0.1)
            cuboid([base_width - 1.6, base_depth - 1.6, 11.7], rounding=0.7, edges="Z", anchor=BOTTOM);
        }
    }
}

module turntable() {
    turntable_base();
    spinning_platter();
    tonearm_assembly();
    dust_cover();
}

// Render the completed assembly
turntable();

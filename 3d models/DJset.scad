/* [Dimensions] */
body_length = 320;      // [200:10:400]
body_height = 140;      // [100:5:200]
body_width = 160;       // [100:5:250]
ground_clearance = 45;  // [20:5:80]
wall_thickness = 6;     // [2:1:10]

/* [Visibility & Interior] */
interior_layout = "DJ Stage"; // [Camper, DJ Stage]
cutaway_view = true;    // [true, false]
shell_alpha = 1.0;      // [0.1:0.1:1.0]

/* [Wheels and Axle] */
wheel_radius = 35;      // [20:1:60]
wheel_thickness = 26;   // [10:1:40]
axle_offset_x = 190;    // [100:10:300]
fender_width = 36;      // [20:2:50]

/* [Colors] */
body_color = "Gainsboro";
door_color = "White";
chassis_color = "Black";
wheel_color = "DarkSlateGray";
rim_color = "Silver";
fender_color = "SteelBlue";
trim_color = "LightGray";

/* [Hidden] */
$fn = 64;
chassis_h = 10;
body_z = ground_clearance + chassis_h;
eps = 0.05;

// Calculated true wheel center based on torsion arm drop
wheel_center_x = axle_offset_x + 20;
wheel_center_z = wheel_radius; 
wheel_center_y = body_width/2 + 5 + wheel_thickness/2;
bulkhead_x = body_length * 0.68; // Divider between main cabin and galley

// The perfect parametric teardrop profile
module teardrop_2d() {
    hull() {
        translate([body_height/5, body_height/5]) circle(r=body_height/5);
        translate([body_height/2, body_height*0.55]) circle(r=body_height/2);
        translate([body_length*0.35, body_height - body_height/5]) circle(r=body_height/5);
        translate([body_length - body_height/10, body_height/10]) circle(r=body_height/10);
    }
    translate([body_height/5, 0]) square([body_length - body_height/5 - body_height/10, body_height/5]);
}

// Inner cavity profile for hollowing out
module teardrop_inner() {
    offset(r=-wall_thickness) teardrop_2d();
}

module roof_trim() {
    difference() {
        teardrop_2d();
        offset(r=-3) teardrop_2d();
    }
}

// --- DJ Equipment Modules ---
module turntable() {
    // Turntable Base
    color("Silver") cube([35, 30, 4], center=true);
    // Platter
    color("DimGray") translate([-3, 0, 2]) cylinder(h=2, r=12, center=true);
    // Vinyl Record
    color("Black") translate([-3, 0, 3.1]) cylinder(h=1, r=11.5, center=true);
    // Record Label
    color("IndianRed") translate([-3, 0, 3.65]) cylinder(h=0.1, r=4, center=true);
    // Tonearm Base
    color("Gray") translate([12, -10, 3]) cylinder(h=6, r=3, center=true);
    // Tonearm Tube
    color("LightGray") translate([5, -7, 6]) rotate([0, 0, -25]) cube([18, 1.5, 1.5], center=true);
    // Stylus/Headshell
    color("Black") translate([-3, -3.5, 5.5]) cube([2, 5, 2.5], center=true);
}

module dj_mixer() {
    color("DarkSlateGray") cube([24, 30, 4], center=true);
    // Crossfader & Line Faders
    for(x=[-5, 5]) {
        color("Black") translate([x, -8, 2.1]) cube([1.5, 10, 2], center=true);
        color("Silver") translate([x, -10, 3]) cube([3, 4, 2], center=true);
    }
    color("Black") translate([0, -12, 2.1]) cube([12, 1.5, 2], center=true);
    color("Silver") translate([0, -12, 3]) cube([4, 3, 2], center=true);
    // EQ Knobs
    for(x=[-6, 0, 6]) {
        for(y=[0, 6, 11]) {
            color("Silver") translate([x, y, 2.5]) cylinder(h=3, r=1.5, center=true, $fn=16);
        }
    }
}

module dj_speaker() {
    color("#1a1a1a") cube([25, 22, 45], center=true);
    // Main Woofer Cone
    color("LightGray") translate([0, 11, -6]) rotate([90, 0, 0]) cylinder(h=2, r=8, center=true);
    color("Black") translate([0, 11.5, -6]) rotate([90, 0, 0]) cylinder(h=1, r=3, center=true);
    // Tweeter
    color("LightGray") translate([0, 11, 12]) rotate([90, 0, 0]) cylinder(h=2, r=3.5, center=true);
    color("Black") translate([0, 11.5, 12]) rotate([90, 0, 0]) cylinder(h=1, r=1, center=true);
}

module dj_booth() {
    // DJ Table base structure
    color("DimGray") translate([0, 0, 15]) cube([120, 25, 30], center=true);
    // Table Top
    color("Black") translate([0, 0, 31]) cube([135, 45, 4], center=true);

    // LP Player Left
    translate([-38, 0, 35]) turntable();
    // LP Player Right
    translate([38, 0, 35]) turntable();
    // Mixer in the middle
    translate([0, 0, 35]) dj_mixer();

    // Speakers at the edges
    translate([-85, 0, 38]) dj_speaker();
    translate([85, 0, 38]) dj_speaker();
}

module interior() {
    intersection() {
        // Bounding inner cavity so nothing pokes out of the shell
        translate([0, 0, body_z])
        rotate([90, 0, 0])
        linear_extrude(body_width - 2*wall_thickness, center=true)
        teardrop_inner();
        
        union() {
            // --- Divider Bulkhead ---
            color("BurlyWood")
            translate([bulkhead_x, -body_width/2, body_z])
            cube([wall_thickness, body_width, 65]);
            
            // Glass plate separating main area from galley
            color("LightCyan", 0.4)
            translate([bulkhead_x, -body_width/2, body_z + 65])
            cube([wall_thickness, body_width, body_height]);
            
            // --- Rear Galley (Kitchenette) ---
            color("SaddleBrown")
            translate([bulkhead_x + wall_thickness, -body_width/2, body_z])
            cube([body_length, body_width, 45]); // Lower Cabinets
            
            color("Peru")
            translate([bulkhead_x + wall_thickness, -body_width/2, body_z + 45])
            cube([body_length, body_width, 5]); // Countertop
            
            color("SaddleBrown")
            translate([bulkhead_x + wall_thickness, -body_width/2, body_z + 90])
            cube([35, body_width, body_height]); // Upper Cupboards
            
            color("DimGray")
            translate([bulkhead_x + wall_thickness + 10, -20, body_z + 50])
            cube([25, 40, 5]); // Stove base
            
            color("Black") {
                translate([bulkhead_x + wall_thickness + 20, -10, body_z + 55]) cylinder(h=2, r=6);
                translate([bulkhead_x + wall_thickness + 20, 10, body_z + 55]) cylinder(h=2, r=6);
            }
            
            color("Silver")
            translate([bulkhead_x + wall_thickness + 10, body_width/4 - 15, body_z + 49])
            difference() {
                cube([25, 30, 6]);
                translate([2, 2, 2]) cube([21, 26, 5]);
            }
            
            color("Silver")
            translate([bulkhead_x + wall_thickness + 14, body_width/4, body_z + 55])
            cylinder(h=10, r=1.5); // Faucet

            // --- Front Main Cabin ---
            if (interior_layout == "DJ Stage") {
                // Inside turned 90 degrees: A fully equipped DJ Booth facing the side door
                translate([body_length * 0.42, -25, body_z])
                dj_booth();
            } else {
                // Classic Camper Bed Setup
                color("Wheat")
                translate([0, -body_width/2, body_z])
                cube([bulkhead_x, body_width, 15]); // Bed base
                
                color("IndianRed")
                translate([20, -body_width/2, body_z + 14])
                cube([bulkhead_x - 60, body_width, 4]); // Blanket
                
                color("White") {
                    translate([bulkhead_x - 30, body_width/4 - 15, body_z + 15]) cube([20, 30, 8]);
                    translate([bulkhead_x - 30, -body_width/4 - 15, body_z + 15]) cube([20, 30, 8]);
                }
                
                // Kid's suspended bunk bed
                color("BurlyWood")
                translate([15, -body_width/2, body_z + 65])
                cube([55, body_width, 5]); 
                
                color("LightBlue")
                translate([15, -body_width/2, body_z + 70])
                cube([55, body_width, 6]); 
                
                color("LightCyan", 0.4)
                translate([70, -body_width/2, body_z + 65])
                cube([2, body_width, 25]); // Glass safety plate
            }
        }
    }
}

module body() {
    // Outer Shell
    difference() {
        color(body_color, shell_alpha)
        translate([0, 0, body_z])
        rotate([90, 0, 0])
        linear_extrude(body_width, center=true)
        teardrop_2d();

        // Inner void
        translate([0, 0, body_z])
        rotate([90, 0, 0])
        linear_extrude(body_width - 2*wall_thickness, center=true)
        teardrop_inner();
        
        // Cutaway Box for visibility
        if (cutaway_view) {
            translate([-50, 0, -50])
            cube([body_length + 100, body_width, body_height + ground_clearance + 100]);
        }
    }

    // Call Interior
    interior();

    // Edge Trim
    color(trim_color)
    difference() {
        translate([0, 0, body_z])
        rotate([90, 0, 0])
        linear_extrude(body_width + 4, center=true)
        roof_trim();
        
        if (cutaway_view) {
            translate([-50, 0, -50])
            cube([body_length + 100, body_width + 10, body_height + ground_clearance + 100]);
        }
    }
    
    // Side Doors and Handholds
    for(y_dir = [1, -1]) {
        if (!cutaway_view || y_dir < 0) {
            y = y_dir * (body_width/2 + 1);
            
            translate([body_length*0.35, y, body_z + 20])
            color(door_color)
            hull() {
                translate([15, 0, 15]) rotate([90, 0, 0]) cylinder(h=2, r=15, center=true);
                translate([60, 0, 15]) rotate([90, 0, 0]) cylinder(h=2, r=15, center=true);
                translate([15, 0, 75]) rotate([90, 0, 0]) cylinder(h=2, r=15, center=true);
                translate([60, 0, 75]) rotate([90, 0, 0]) cylinder(h=2, r=15, center=true);
            }
            
            translate([body_length*0.35, y + (y>0 ? 1 : -1), body_z + 20])
            color(chassis_color)
            hull() {
                translate([20, 0, 45]) rotate([90, 0, 0]) cylinder(h=2.5, r=10, center=true);
                translate([55, 0, 45]) rotate([90, 0, 0]) cylinder(h=2.5, r=10, center=true);
                translate([20, 0, 70]) rotate([90, 0, 0]) cylinder(h=2.5, r=10, center=true);
                translate([55, 0, 70]) rotate([90, 0, 0]) cylinder(h=2.5, r=10, center=true);
            }
            
            translate([body_length*0.35 + 10, y + (y>0 ? 1.5 : -1.5), body_z + 55])
            color(rim_color)
            rotate([90, 0, 0]) cylinder(h=3, r=2, center=true, $fn=16);
        }
    }

    // Rear Hatch Handle
    color(rim_color)
    difference() {
        translate([body_length - 8, 0, body_z + body_height*0.3])
        rotate([90, 0, 0]) cylinder(h=body_width*0.6, r=2, center=true);
        
        if(cutaway_view) {
            translate([body_length - 20, 0, -50])
            cube([40, body_width, body_height + 100]);
        }
    }

    // Roof Vent
    color(trim_color)
    difference() {
        translate([body_length*0.45, 0, body_z + body_height - 5])
        cube([40, 40, 12], center=true);
        if(cutaway_view) {
            translate([-50, 0, -50])
            cube([body_length + 100, body_width, body_height + ground_clearance + 100]);
        }
    }
}

module chassis() {
    color(chassis_color) {
        for(y_dir = [1, -1]) {
            if (!cutaway_view || y_dir < 0) {
                y = y_dir * (body_width/2 - 5);
                translate([0, y - 5, ground_clearance])
                cube([body_length, 10, chassis_h]);
            }
        }
        for(x = [10, body_length/4, body_length/2, body_length*3/4, body_length-15]) {
            difference() {
                translate([x, -body_width/2 + 5, ground_clearance])
                cube([10, body_width - 10, chassis_h]);
                if (cutaway_view) {
                    translate([x-5, 0, ground_clearance-5])
                    cube([20, body_width, chassis_h+10]);
                }
            }
        }
        hull() {
            translate([-70, -5, ground_clearance]) cube([10, 10, chassis_h]);
            translate([0, -body_width/2 + 5, ground_clearance]) cube([10, 10, chassis_h]);
        }
        if (!cutaway_view) {
            hull() {
                translate([-70, -5, ground_clearance]) cube([10, 10, chassis_h]);
                translate([0, body_width/2 - 15, ground_clearance]) cube([10, 10, chassis_h]);
            }
        }
        
        translate([-85, 0, ground_clearance]) cylinder(h=15, r=4);
        translate([-60, 0, ground_clearance]) cylinder(h=30, r=3, center=true);
        translate([-60, 0, ground_clearance - 25]) cylinder(h=5, r=8, center=true);
        translate([-60, 0, ground_clearance + 20]) cylinder(h=4, r=10, center=true);
    }
}

module suspension() {
    color(chassis_color) {
        difference() {
            translate([axle_offset_x, 0, ground_clearance + 5])
            rotate([90, 0, 0]) cylinder(h=body_width - 10, r=8, center=true);
            if (cutaway_view) {
                translate([axle_offset_x-10, 0, ground_clearance-10]) cube([20, body_width, 30]);
            }
        }
        for(y_dir = [1, -1]) {
            if (!cutaway_view || y_dir < 0) {
                y = y_dir * (body_width/2 - 5);
                translate([axle_offset_x, y, ground_clearance + 5])
                hull() {
                    rotate([90, 0, 0]) cylinder(h=10, r=10, center=true);
                    translate([20, 0, -15]) rotate([90, 0, 0]) cylinder(h=10, r=6, center=true);
                }
            }
        }
    }
    
    color(trim_color)
    for(y_dir = [1, -1]) {
        if (!cutaway_view || y_dir < 0) {
            y = y_dir * (body_width/2 + wheel_thickness/2);
            translate([wheel_center_x, y, wheel_center_z])
            rotate([90, 0, 0]) cylinder(h=wheel_thickness + 20, r=4, center=true);
        }
    }
}

module wheel_assembly() {
    for(y_dir = [1, -1]) {
        if (!cutaway_view || y_dir < 0) {
            y = y_dir * wheel_center_y;
            translate([wheel_center_x, y, wheel_center_z]) {
                
                color(wheel_color)
                hull() {
                    translate([0, wheel_thickness/2 - 4, 0])
                    rotate([90, 0, 0])
                    rotate_extrude() translate([wheel_radius - 4, 0]) circle(r=4);

                    translate([0, -(wheel_thickness/2 - 4), 0])
                    rotate([90, 0, 0])
                    rotate_extrude() translate([wheel_radius - 4, 0]) circle(r=4);
                }

                color(rim_color)
                rotate([90, 0, 0])
                difference() {
                    cylinder(h=wheel_thickness + eps, r=wheel_radius - 10, center=true);
                    translate([0, 0, y > 0 ? 5 : -5]) cylinder(h=wheel_thickness, r=wheel_radius - 15, center=true);
                    for(a = [0:72:359]) {
                        rotate([0, 0, a])
                        translate([wheel_radius - 22, 0, 0])
                        cylinder(h=wheel_thickness + 10, r=6, center=true);
                    }
                    cylinder(h=wheel_thickness + 10, r=3, center=true);
                }

                color(trim_color)
                translate([0, y > 0 ? (wheel_thickness/2 - 2) : -(wheel_thickness/2 - 2), 0])
                sphere(r=7);
            }
        }
    }
}

module fenders() {
    for(y_dir = [1, -1]) {
        if (!cutaway_view || y_dir < 0) {
            y = y_dir * wheel_center_y;
            color(fender_color)
            translate([wheel_center_x, y, wheel_center_z]) {
                difference() {
                    rotate([90, 0, 0]) cylinder(h=fender_width, r=wheel_radius + 14, center=true);
                    rotate([90, 0, 0]) cylinder(h=fender_width + 2, r=wheel_radius + 10, center=true);
                    translate([-100, -50, -100]) cube([200, 100, 100]);
                }
                translate([0, y > 0 ? -fender_width/2 + 2 : fender_width/2 - 2, 0])
                difference() {
                    rotate([90, 0, 0]) cylinder(h=4, r=wheel_radius + 14, center=true);
                    rotate([90, 0, 0]) cylinder(h=6, r=wheel_radius + 10, center=true);
                    translate([-100, -10, -100]) cube([200, 20, 100]);
                }
            }
        }
    }
}

// Assemble the Caravan
union() {
    chassis();
    suspension();
    wheel_assembly();
    fenders();
    body();
}

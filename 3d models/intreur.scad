/* [Dimensions] */
body_length = 320;      // [200:10:400]
body_height = 140;      // [100:5:200]
body_width = 160;       // [100:5:250]
ground_clearance = 45;  // [20:5:80]
wall_thickness = 6;     // [2:1:10]

/* [Visibility & Interior] */
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
bulkhead_x = body_length * 0.68; // Divider between sleeping and galley

// The perfect parametric teardrop profile
module teardrop_2d() {
    hull() {
        // Front lower corner
        translate([body_height/5, body_height/5]) circle(r=body_height/5);
        // Front upper curve
        translate([body_height/2, body_height*0.55]) circle(r=body_height/2);
        // Mid-upper peak
        translate([body_length*0.35, body_height - body_height/5]) circle(r=body_height/5);
        // Rear tail
        translate([body_length - body_height/10, body_height/10]) circle(r=body_height/10);
    }
    // Fill the flat bottom completely
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

// Full interior setup, automatically clipped to fit inside the teardrop curve
module interior() {
    intersection() {
        // Bounding inner cavity
        translate([0, 0, body_z])
        rotate([90, 0, 0])
        linear_extrude(body_width - 2*wall_thickness, center=true)
        teardrop_inner();
        
        union() {
            // --- 1. Sleeping Cabin (Main Area) ---
            
            // Main 2-Person Bed Base
            color("Wheat")
            translate([0, -body_width/2, body_z])
            cube([bulkhead_x, body_width, 15]);
            
            // Main Bed Blanket
            color("IndianRed")
            translate([20, -body_width/2, body_z + 14])
            cube([bulkhead_x - 60, body_width, 4]);
            
            // Pillows at rear of main bed (near bulkhead)
            color("White") {
                translate([bulkhead_x - 30, body_width/4 - 15, body_z + 15]) cube([20, 30, 8]);
                translate([bulkhead_x - 30, -body_width/4 - 15, body_z + 15]) cube([20, 30, 8]);
            }
            
            // Kid's suspended bunk bed (Top layer at front)
            color("BurlyWood")
            translate([15, -body_width/2, body_z + 65])
            cube([55, body_width, 5]); // Bunk base
            
            color("LightBlue")
            translate([15, -body_width/2, body_z + 70])
            cube([55, body_width, 6]); // Bunk mattress
            
            // Glass plate separating kid bunk from main open space
            color("LightCyan", 0.4)
            translate([70, -body_width/2, body_z + 65])
            cube([2, body_width, 25]); 
            
            // --- 2. Divider Bulkhead ---
            
            // Lower solid wood bulkhead
            color("BurlyWood")
            translate([bulkhead_x, -body_width/2, body_z])
            cube([wall_thickness, body_width, 65]);
            
            // Glass plate separating main area from galley (upper bulkhead)
            color("LightCyan", 0.4)
            translate([bulkhead_x, -body_width/2, body_z + 65])
            cube([wall_thickness, body_width, body_height]);
            
            // --- 3. Rear Galley (Kitchenette) ---
            
            // Galley Floor & Lower Cabinets
            color("SaddleBrown")
            translate([bulkhead_x + wall_thickness, -body_width/2, body_z])
            cube([body_length, body_width, 45]);
            
            // Galley Countertop
            color("Peru")
            translate([bulkhead_x + wall_thickness, -body_width/2, body_z + 45])
            cube([body_length, body_width, 5]);
            
            // Galley Upper Cupboards (Up storage)
            color("SaddleBrown")
            translate([bulkhead_x + wall_thickness, -body_width/2, body_z + 90])
            cube([35, body_width, body_height]);
            
            // Galley Small Stove
            color("DimGray")
            translate([bulkhead_x + wall_thickness + 10, -20, body_z + 50])
            cube([25, 40, 5]);
            
            // Stove Burners
            color("Black") {
                translate([bulkhead_x + wall_thickness + 20, -10, body_z + 55]) cylinder(h=2, r=6);
                translate([bulkhead_x + wall_thickness + 20, 10, body_z + 55]) cylinder(h=2, r=6);
            }
            
            // Small Galley Sink
            color("Silver")
            translate([bulkhead_x + wall_thickness + 10, body_width/4 - 15, body_z + 49])
            difference() {
                cube([25, 30, 6]); // Rim
                translate([2, 2, 2]) cube([21, 26, 5]); // Bowl
            }
            // Sink Faucet
            color("Silver")
            translate([bulkhead_x + wall_thickness + 14, body_width/4, body_z + 55])
            cylinder(h=10, r=1.5);
        }
    }
}

module body() {
    // Outer Shell with hollowing and cutaway
    difference() {
        // Main solid shell
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

    // Interior Furniture
    interior();

    // Aluminum Edge Trim
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
    
    // Side Doors and Details
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
            
            // Window
            translate([body_length*0.35, y + (y>0 ? 1 : -1), body_z + 20])
            color(chassis_color)
            hull() {
                translate([20, 0, 45]) rotate([90, 0, 0]) cylinder(h=2.5, r=10, center=true);
                translate([55, 0, 45]) rotate([90, 0, 0]) cylinder(h=2.5, r=10, center=true);
                translate([20, 0, 70]) rotate([90, 0, 0]) cylinder(h=2.5, r=10, center=true);
                translate([55, 0, 70]) rotate([90, 0, 0]) cylinder(h=2.5, r=10, center=true);
            }
            
            // Door Handle
            translate([body_length*0.35 + 10, y + (y>0 ? 1.5 : -1.5), body_z + 55])
            color(rim_color)
            rotate([90, 0, 0]) cylinder(h=3, r=2, center=true, $fn=16);
        }
    }

    // Rear Galley Hatch Handle
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
        // Main Rails
        for(y_dir = [1, -1]) {
            if (!cutaway_view || y_dir < 0) {
                y = y_dir * (body_width/2 - 5);
                translate([0, y - 5, ground_clearance])
                cube([body_length, 10, chassis_h]);
            }
        }
        
        // Crossbars
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
        
        // A-Frame
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
        
        // Hitch coupling & Jack
        translate([-85, 0, ground_clearance]) cylinder(h=15, r=4);
        translate([-60, 0, ground_clearance]) cylinder(h=30, r=3, center=true);
        translate([-60, 0, ground_clearance - 25]) cylinder(h=5, r=8, center=true);
        translate([-60, 0, ground_clearance + 20]) cylinder(h=4, r=10, center=true);
    }
}

module suspension() {
    color(chassis_color) {
        // Main Torsion Tube
        difference() {
            translate([axle_offset_x, 0, ground_clearance + 5])
            rotate([90, 0, 0]) cylinder(h=body_width - 10, r=8, center=true);
            if (cutaway_view) {
                translate([axle_offset_x-10, 0, ground_clearance-10]) cube([20, body_width, 30]);
            }
        }

        // Trailing Arms
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
    
    // Axle Stubs
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
                
                // Tire
                color(wheel_color)
                hull() {
                    translate([0, wheel_thickness/2 - 4, 0])
                    rotate([90, 0, 0])
                    rotate_extrude() translate([wheel_radius - 4, 0]) circle(r=4);

                    translate([0, -(wheel_thickness/2 - 4), 0])
                    rotate([90, 0, 0])
                    rotate_extrude() translate([wheel_radius - 4, 0]) circle(r=4);
                }

                // Rim
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

                // Hubcap
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

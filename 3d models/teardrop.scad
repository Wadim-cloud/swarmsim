/* [Dimensions] */
body_length = 320;      // [200:10:400]
body_height = 140;      // [100:5:200]
body_width = 160;       // [100:5:250]
ground_clearance = 45;  // [20:5:80]

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
light_color = "Red";
accent_color = "DarkGray";

/* [Hidden] */
$fn = 64;
chassis_h = 10;
body_z = ground_clearance + chassis_h;
eps = 0.05;

// Calculated true wheel center based on torsion arm drop
wheel_center_x = axle_offset_x + 20;
wheel_center_z = wheel_radius; 
wheel_center_y = body_width/2 + 5 + wheel_thickness/2;

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

module roof_trim() {
    difference() {
        teardrop_2d();
        offset(r=-3) teardrop_2d();
    }
}

module body() {
    // Main Shell
    color(body_color)
    translate([0, -body_width/2, body_z])
    rotate([90, 0, 0])
    linear_extrude(body_width, center=false)
    teardrop_2d();

    // Aluminum Edge Trim
    color(trim_color)
    translate([0, body_width/2 + 2, body_z])
    rotate([90, 0, 0])
    linear_extrude(body_width + 4)
    roof_trim();
    
    // Side Doors
    for(y = [body_width/2 + 1, -body_width/2 - 3]) {
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

    // Rear Galley Hatch Handle
    color(rim_color)
    translate([body_length - 8, 0, body_z + body_height*0.3])
    rotate([90, 0, 0]) cylinder(h=body_width*0.6, r=2, center=true);

    // Roof Vent
    color(trim_color)
    translate([body_length*0.45, 0, body_z + body_height - 5])
    cube([40, 40, 12], center=true);
    
    // Taillights
    color(light_color)
    for(y = [body_width/2 - 15, -body_width/2 + 15]) {
        translate([body_length - 4, y, body_z + 25])
        rotate([0, 90, 0])
        cylinder(h=6, r=6, center=true);
    }
}

module chassis() {
    color(chassis_color) {
        // Main Rails
        for(y = [body_width/2 - 5, -body_width/2 + 5]) {
            translate([0, y - 5, ground_clearance])
            cube([body_length, 10, chassis_h]);
        }
        
        // Crossbars
        for(x = [10, body_length/4, body_length/2, body_length*3/4, body_length-15]) {
            translate([x, -body_width/2 + 5, ground_clearance])
            cube([10, body_width - 10, chassis_h]);
        }
        
        // A-Frame
        hull() {
            translate([-70, -5, ground_clearance]) cube([10, 10, chassis_h]);
            translate([0, -body_width/2 + 5, ground_clearance]) cube([10, 10, chassis_h]);
        }
        hull() {
            translate([-70, -5, ground_clearance]) cube([10, 10, chassis_h]);
            translate([0, body_width/2 - 15, ground_clearance]) cube([10, 10, chassis_h]);
        }
        
        // Hitch coupling
        translate([-85, 0, ground_clearance]) cylinder(h=15, r=4);
        
        // Tongue Jack post
        translate([-60, 0, ground_clearance]) cylinder(h=30, r=3, center=true);
        translate([-60, 0, ground_clearance - 25]) cylinder(h=5, r=8, center=true);
        translate([-60, 0, ground_clearance + 20]) cylinder(h=4, r=10, center=true);
    }

    // Hitch Ball
    color(rim_color)
    translate([-85, 0, ground_clearance+15]) sphere(r=5);

    // Propane Tank
    color(door_color) {
        translate([-45, 0, ground_clearance + chassis_h + 10]) {
            cylinder(h=25, r=12, center=true);
            translate([0, 0, 12]) sphere(r=12);
            translate([0, 0, -12]) sphere(r=12);
        }
    }
    // Propane Valve
    color(trim_color)
    translate([-45, 0, ground_clearance + chassis_h + 35])
    cylinder(h=5, r=4, center=true);

    // Battery Box
    color(chassis_color)
    translate([-20, 0, ground_clearance + chassis_h + 10])
    cube([25, 40, 20], center=true);
}

module suspension() {
    color(chassis_color) {
        // Main Torsion Tube
        translate([axle_offset_x, 0, ground_clearance + 5])
        rotate([90, 0, 0]) cylinder(h=body_width - 10, r=8, center=true);

        // Trailing Arms
        for(y = [body_width/2 - 5, -body_width/2 + 5]) {
            translate([axle_offset_x, y, ground_clearance + 5])
            hull() {
                rotate([90, 0, 0]) cylinder(h=10, r=10, center=true);
                translate([20, 0, -15]) rotate([90, 0, 0]) cylinder(h=10, r=6, center=true);
            }
        }
    }
    
    // Axle Stubs (visible behind wheels)
    color(trim_color)
    translate([wheel_center_x, 0, wheel_center_z])
    rotate([90, 0, 0]) cylinder(h=body_width + 20 + wheel_thickness, r=4, center=true);
}

module wheel_assembly() {
    for(y = [wheel_center_y, -wheel_center_y]) {
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
                
                // Deep dish
                translate([0, 0, y > 0 ? 5 : -5])
                cylinder(h=wheel_thickness, r=wheel_radius - 15, center=true);
                
                // Spoke cutouts
                for(a = [0:72:359]) {
                    rotate([0, 0, a])
                    translate([wheel_radius - 22, 0, 0])
                    cylinder(h=wheel_thickness + 10, r=6, center=true);
                }
                
                // Center hole
                cylinder(h=wheel_thickness + 10, r=3, center=true);
            }

            // Hubcap
            color(trim_color)
            translate([0, y > 0 ? (wheel_thickness/2 - 2) : -(wheel_thickness/2 - 2), 0])
            sphere(r=7);
        }
    }
}

module fenders() {
    for(y = [wheel_center_y, -wheel_center_y]) {
        color(fender_color)
        translate([wheel_center_x, y, wheel_center_z]) {
            difference() {
                // Main outer shell
                rotate([90, 0, 0]) cylinder(h=fender_width, r=wheel_radius + 14, center=true);
                // Inner hollow
                rotate([90, 0, 0]) cylinder(h=fender_width + 2, r=wheel_radius + 10, center=true);
                // Cut lower half
                translate([-100, -50, -100]) cube([200, 100, 100]);
            }
            
            // Outer curved lip
            translate([0, y > 0 ? -fender_width/2 + 2 : fender_width/2 - 2, 0])
            difference() {
                rotate([90, 0, 0]) cylinder(h=4, r=wheel_radius + 14, center=true);
                rotate([90, 0, 0]) cylinder(h=6, r=wheel_radius + 10, center=true);
                translate([-100, -10, -100]) cube([200, 20, 100]);
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

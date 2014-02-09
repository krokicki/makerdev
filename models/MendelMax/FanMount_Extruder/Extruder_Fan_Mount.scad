/* 
 * MakerDev Extruder fan mount for MendelMax, heavily based on the Brix Extruder Fan Mount for Prusa
 * (http://www.thingiverse.com/thing:19076)
 * 
 * Modified to include a longer nozzle for more localized cooling, and mounting holes that 
 * fit the MendelMax X Carriage from 3dsuppli (http://www.thingiverse.com/thing:59297)
 * 
 * Copyright 2014 MakerDev
 * License: CC BY-SA
 */

// Rendering
$fs=0.5;
$fa=5;

module fan_mount(panel_thickness, mounting_hole_distance) {
	fan_dia = 41.25;
	screw_dia = 3;
	nut_dia = 5.5;
	nut_thickness = 2.5;

	module nuttrap(nutsize, length) {
		cylinder(r = nutsize / cos(180 / 6) / 2 + 0.05, length, $fn=6);
	}

	union() {
		difference() {
			union() {
				// Outer frame
				hull() {
					for (i = [1, -1]) {
						for (j = [1, -1]) {
							translate([i * fan_dia / 2 - i * fan_dia / 10,
									   j * fan_dia / 2 - j * fan_dia / 10, 0]) {
								rotate([0, 0, 90]) {
									cylinder(r = fan_dia / 10, panel_thickness);
								}
							}
						}
					}
				}

				// Nut trap outlines
				for (i = [1, -1]) {
					for (j = [1, -1]) {
						translate([i * fan_dia / 2 - i * fan_dia / 10,
								   j * fan_dia / 2 - j * fan_dia / 10, 0]) {
							rotate([0, 0, 90]) {
								cylinder(r = fan_dia / 10, panel_thickness + nut_thickness);
							}
						}
					}
				}

				// Long funnel
				cylinder(r1 = fan_dia / 2, r2 = fan_dia / 2.625, h = 50);
			}

			// Screw holes
			for (i = [1, -1]) {
				for (j = [1, -1]) {
					translate([i * fan_dia / 2 - i * fan_dia / 10,
							   j * fan_dia / 2 - j * fan_dia / 10,
							 -panel_thickness]) {
						rotate([0, 0, 90]) {
							cylinder(r = screw_dia / 2, panel_thickness * 2 + nut_thickness * 2);
						}
					}
				}
			}

			// Nut traps
			for (i = [1, -1]) {
				for (j = [1, -1]) {
					translate([i * fan_dia / 2 - i * fan_dia / 10,
							   j * fan_dia / 2 - j * fan_dia / 10,
							   panel_thickness]) {
						rotate([0, 0, i * j * 15]) {
							nuttrap(nut_dia, nut_thickness * 2);
						}
					}
				}
			}
	
			// Funnel cut-out
			translate([0, 0, -0.5]) {
				cylinder(r1 = fan_dia / 2 - panel_thickness, r2 = fan_dia / 2.625 - panel_thickness, h = 61);
			}

			// Funnel cut-off
			rotate([0, -65, 0]) {
				translate([fan_dia / 2 - 5, 0, fan_dia]) {
					cube([fan_dia+45, fan_dia, fan_dia], center = true);
				}
			}
		}

		// Funnel bottom close-off
		rotate([0, -65, 0]) {
			translate([fan_dia / 2 - 5 + 7.5, 0, fan_dia-21.5]) {
				cube([fan_dia+1, fan_dia-25, 2], center = true);
			}
			translate([fan_dia / 2 - 5 + 11, 0, fan_dia-21.5]) {
				cube([fan_dia - 4, fan_dia-18.5, 2], center = true);
			}
			translate([fan_dia / 2 - 5 + 14, 0, fan_dia-21.5]) {
				cube([fan_dia - 12, fan_dia-14, 2], center = true);
			}
			translate([fan_dia / 2 - 5 + 19, 0, fan_dia-21.5]) {
				cube([fan_dia - 19.5, fan_dia-11, 2], center = true);
			}
		}
	}
}

module mountEar(mountHeight = 10){
	rotate([0,90,0]) {
		 difference(){
			union(){
			 cylinder(r=5, h=3.5-wiggle, center=true);
			 translate([mountHeight/2,0,0])
			 cube([mountHeight, 10, 3.5-wiggle], center=true);
			}
			cylinder(r=1.5+wiggle, h=3.5, center=true);
		}
	}
}


// This part goes on the fan
module fanMountingBracket(mountHeight = 10, mountSpacing = 2){
	union(){
		// bottom
		cube([10,10,2], center=true);
		// 2x mount ears
		for (i = [1,-1]){
		 translate([i*mountSpacing,0,mountHeight])
		 mountEar(mountHeight);
		}
	}
}

// This part goes on the carriage, mates the fan to the prusaMountingEars
module mountEars(mountHeight = 10, mountSpacing = 2){		
 difference(){	
  union(){	   		
	rotate([90,0,0])
	// 3x mount ears
	union(){
		for (i = [2,0,-2]){
		 translate([i*mountSpacing, 0, mountHeight])
		 mountEar(mountHeight);
		}
	}
  }
 }
}

// A rounded rectangle that looks like a long pill
module pill(length, r=5, h=2){
     hull() {
        translate([length, 0, 0]) cylinder(r=r, h=h);
        translate([0, 0, 0]) cylinder(r=r, h=h);
    }
}

// This part goes on the carriage, mates the fan to the prusaMountingEars
module carriageMountingBracket(mountHeight = 10, mountSpacing = 3.2){		
	union() {	
        // U-Bracket
	    difference() {
	        union() {
	            translate([7, 18, 0]) pill(18);
	            translate([7, -18, 0]) pill(18);
	            translate([7, -18, 0]) rotate([0, 0, 90]) pill(36);
	            translate([12, -18, 0]) rotate([0, 0, 90]) pill(36);
	        }
            // Inner curve
	        translate([18, -8, -1]) rotate([0, 0, 90]) pill(16, h=5);
	        // Mounting holes
			translate([7, -18, -1]) cylinder(r=2, h=5);
	        translate([7, 18, -1]) cylinder(r=2, h=5);
	        translate([25, -18, -1]) cylinder(r=2, h=5);
	        translate([25, 18, -1]) cylinder(r=2, h=5);
	    }
        // Rounded part
		intersection() {
			translate([2, -8, 0]) cube([12, 16, 10]);
			translate([3, 8, 2]) rotate([90, 0, 0]) cylinder(r=8, h=16);
		}
        // Mount ears
		translate([3,0,5]) rotate([180,0,90]) mountEars(mountHeight, mountSpacing);
	}
}

// STL Creation / mockup mode options
printPart = "mount"; // values "fan", "mount", "mockup"

wiggle=0.1; // values 0.1 - 0.2 seem about right.  

if (printPart == "fan" || printPart=="mockup"){
 color("IndianRed")
 union(){
	fan_mount(2, 22);
	translate([19,0,5])
	rotate([90,0,90])
	fanMountingBracket(10, 3.2);	
 }
}

if (printPart == "mockup"){ 
  rotate([180,0,0])
  translate([36,0,-10])
  color("oliveDrab") carriageMountingBracket(10, 3.2);
}

if (printPart == "mount"){
 translate([0,8,0])
 rotate([0,0,0])
 color("oliveDrab") carriageMountingBracket(10, 3.2);
}

# rigify_bendy (Rigify Extension)
Rigify extension with REAL bendy bone controls and improved metarigs

![Rigify Bendy Description](/images/rigify_bendy.jpg)

### Use real Bendy Bone controls in your Rigify rigs

This extension adds limbs to Rigify that work exactly like the built-in modules, but improve the 'Tweak'-control layer.

## How to set it up

* Download as .zip
* Open Blender, Preferences, Add-ons, and search for/activate Rigify
* Open "External Feature Sets", "Install Feature Set from File..." and navigate to the downloaded .zip
* That's it!

To use the rigs, either change existing Rig types from "limb.[...]" to "limb_bendy.[...]" or start adding new samples to a fresh rig.

### Super quick start:
> Add > Armature > Bendy > Bendy Human

## How to use it

I tried to keep the controls as intuitive as possible, while giving maximum control over curvature and scaling.
Use the rig just as you're used to, but pay attention to the 'Tweaks' layers...

### Think of Bezier Curves
* Locations: You can now freely and independently tweak every subsegment
* Rotations: All rotations are unlocked. Y rotation will be added to already existing segment roll
* Scale X, Z: Scaling along those axes controls the shape scale respectively
* Scale Y: Scaling along the Y axis controls the curvature

As an animator, the only thing to keep in mind is that you shouldn't just go for uniform scaling, since the scaling in Y direction now affects the curve!

## How it works

I based the limbs on the built-in Rigify limbs. Only the Tweak bones and Bendy Bone properties for Deform bones changed, everything else is the same.
The 'Tweak' segments are not based on Copy Transform Constraints anymore and all transforms are fully unlocked.
Their rotation and scaling now fully drive the bendy properties of the Deform bones. Segment roll is driven as well.

## Development

I'm open for testing & feedback! I'm planning on adding the same functionality for the Tail & Spine module, as well as a simple Bendy Bone Tentacle.
Lastly I'm working on a new facial rig making full use of our beloved Bendies. My goal is to extend Rigify to be that tiny step closer to my own feature film quality needs.
Stay tuned!

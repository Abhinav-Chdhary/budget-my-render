# First Fixture: Glossy Sphere

Use this tiny scene for the first manual benchmark:

1. Add a plane, a UV sphere with a low-roughness Principled BSDF material, and a large Area light.
2. Position the camera so the sphere casts a soft shadow across the plane.
3. Save it as `fixtures/glossy-sphere.blend` when ready.
4. Compare 16, 64, 256, and 1024 samples with adaptive sampling and denoising toggled independently.

This fixture intentionally contains a glossy highlight and soft shadow: both make sample/noise trade-offs easy to see.

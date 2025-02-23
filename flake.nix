{
  description = "Development environment for NarrativeSceneGraph";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

  outputs = { self, nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
    in {
      devShells.${system}.default = pkgs.mkShell {
        buildInputs = [
          pkgs.python311        # Use the desired Python version
          pkgs.gcc              # Provides libstdc++
          pkgs.graphviz
          pkgs.python311Packages.numpy        # NumPy package for Python 3.11
        ];

        # Set LD_LIBRARY_PATH to include the gcc libraries
        # shellHook = ''
        #   export LD_LIBRARY_PATH="${pkgs.gcc.libc}/lib:$LD_LIBRARY_PATH"
        #   echo "LD_LIBRARY_PATH set to: $LD_LIBRARY_PATH"
        # '';
      };
    };
}


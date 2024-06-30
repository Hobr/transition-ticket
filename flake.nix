{
  description = "Python Shell";
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShell =
          with pkgs;
          mkShell rec {
            venvDir = ".venv";
            packages =
              with pkgs;
              [
                python312
                poetry
                portaudio
                stdenv.cc.cc.lib
                graphviz
                pre-commit
              ]
              ++ (with pkgs.python312Packages; [
                pip
                venvShellHook
              ]);
            PIP_INDEX_URL = "https://pypi.tuna.tsinghua.edu.cn/simple";
            PIP_TRUSTED_HOST = "pypi.tuna.tsinghua.edu.cn";
            LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath packages;
          };
      }
    );
}

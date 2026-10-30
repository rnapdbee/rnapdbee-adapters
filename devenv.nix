{
  pkgs,
  lib,
  config,
  inputs,
  ...
}:
{
  languages.python = {
    enable = true;
    venv.enable = true;
    uv = {
      enable = true;
      sync.enable = true;
    };
  };
  packages = [ pkgs.zlib ];
  env.LD_LIBRARY_PATH = "${lib.makeLibraryPath [
    pkgs.stdenv.cc.cc.lib
    pkgs.zlib
  ]}";
  enterShell = ''
    export PYTHONPATH=src/
  '';
}

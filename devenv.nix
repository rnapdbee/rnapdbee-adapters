{ pkgs, ... }:
{
  languages.python = {
    enable = true;
    version = "3.14";
    venv = {
      enable = true;
      requirements = ./requirements.txt;
    };
  };
  packages = [ pkgs.zlib ];
  enterShell = ''
    export PYTHONPATH=src/
  '';
}

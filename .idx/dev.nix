# To learn more about how to use Nix to configure your environment
# see: https://developers.google.com/idx/guides/customize-idx-env

{ pkgs, ... }: {
  # Which nixpkgs channel to use.
  channel = "stable-24.05"; # or "unstable"

  # Use https://search.nixos.org/packages to find packages
  packages = [
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.python311Packages.virtualenv
    pkgs.nodejs_20
    pkgs.nodePackages.npm
  ];

  # Sets environment variables in the workspace
  env = {
    AI_BS_ENV = "development_remote";
    PORT = "5173";
  };

  idx = {
    # Search for the extensions you want on https://open-vsx.org/ and use "publisher.id"
    extensions = [
      "ms-python.python",
      "ms-python.debugpy",
      "dbaeumer.vscode-eslint"
    ];

    # Enable previews and configure how to launch applications
    previews = {
      enable = true;
      previews = {
        web = {
          command = [
            "npm"
            "run"
            "dev"
            "--"
            "--port"
            "$PORT"
            "--host"
            "0.0.0.0"
          ];
          manager = "web";
        };
      };
    };

    # Workspace lifecycle hooks
    workspace = {
      # Runs when a workspace is first created with this codebase
      onCreate = {
        npm-install = "npm install";
        setup-venv = "python3 -m venv .venv && source .venv/bin/activate && pip install -r backend/requirements.txt || pip install -r requirements.txt || true";
      };
      # Runs each time the workspace is (re)started
      onStart = {
        # Optional startup hooks
      };
    };
  };
}

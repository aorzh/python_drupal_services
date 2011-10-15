try:
    import distutils
    from distutils import sysconfig
    from distutils.command.install import install
    from distutils.core import setup, Extension
except:
    raise SystemExit("Distutils problem")

setup(name = "drupal_services",
      description = "Access drupal service from python",
      py_modules = ["drupal_services"]
      )

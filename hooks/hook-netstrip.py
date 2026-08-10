from PyInstaller.utils.hooks import collect_all, collect_submodules

datas, binaries, hiddenimports = collect_all('netstrip')

# Explicitly collect all submodules to guarantee PyInstaller includes them
# in the PYZ archive. collect_all sometimes misses deeply nested subpackages
# when they aren't directly reachable through static import analysis.
hiddenimports += collect_submodules('netstrip')
hiddenimports += collect_submodules('netstrip.core')
hiddenimports += collect_submodules('netstrip.core.interceptor')
hiddenimports += collect_submodules('netstrip.core.ebpf')
hiddenimports += collect_submodules('netstrip.gui')
hiddenimports += collect_submodules('netstrip.gui.components')
hiddenimports += collect_submodules('netstrip.gui.views')
hiddenimports += collect_submodules('netstrip.data')
hiddenimports += collect_submodules('netstrip.platform')

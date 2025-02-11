# 获取脚本所在的文件夹路径
$rootFolder = $PSScriptRoot

# 定义 Python 脚本路径
$pythonScript = "$rootFolder\main.py"

# 定义资源文件夹路径
$resourcesFolder = "$rootFolder\resources\*"

# 定义版本号
$version = "1.0.0.1"  # 设置版本号

# 设置输出文件名，包含版本号
$outputFileName = "iw_anno_v$version"

# 进入 Python 脚本所在的目录
Set-Location -Path $rootFolder

# 检查 pyinstaller 是否已安装，如果没有则安装
$pyinstallerInstalled = Get-Command pyinstaller -ErrorAction SilentlyContinue
if (-not $pyinstallerInstalled) {
    Write-Host "PyInstaller not found, installing it..."
    pip install pyinstaller
}

# 执行 pyinstaller 打包命令，使用 --add-data 参数将 resources 文件夹的内容包括进来，并指定版本号文件，修改文件名
Write-Host "Building exe from $pythonScript with version $version..."
pyinstaller --onefile --windowed --add-data "$resourcesFolder;resources" --name "$outputFileName" $pythonScript

Write-Host "Build complete. Check the 'dist' folder for the '$outputFileName.exe' file."

@echo off
pushd "%~dp0.."
python -m tools.cat_extract %* > cat_extract.log 2>&1
type cat_extract.log
popd

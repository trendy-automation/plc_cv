:: enable anaconda environment
set root=D:\Work\miniconda3
call %root%\Scripts\activate.bat %root%

:: start jupyter
pushd %~dp0
call jupyter-lab jupyter\DMU_CV3.ipynb
pause
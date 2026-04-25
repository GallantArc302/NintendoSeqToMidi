for %%i in (*.bsseq *.brseq *.bcseq *.bfseq *.bseq) do (
	python nintendoseq2midi.py %%i %%~ni.mid
)
del log.txt

for %%i in (*.bsseq *.brseq *.bcseq *.bfseq *.bseq) do (
	echo %%i >> log.txt
	python nintendoseq2midi.py "%%i" "%%~ni.mid" >> log.txt
)
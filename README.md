# DrugFinder

DrugFinder (**Corrêa et at, 2019**) is based on the same idea as QuickUMLS (**Soldaini and Goharian, 2016**), 
an unsupervised method for medical concept extraction from clinical text.

DrugFinder uses the DrugBank dataset that contains brand names, generic names, 
and synonyms of medications as well other types of information, 
such as chemical formulas, indications, and interactions. 
We automatically mapped generic names to one or more brand or generic names and synonyms.

**This project should be compatible with Python 3 and run on any UNIX system.**

## Installation

- TODO

## References

- Okazaki and Tsujii, 2010. Simple and Efficient Algorithm for Approximate Dictionary Matching. In Proceedings of the 23rd International Conference on Computational Linguistics (Coling 2010) 
```bibtex
@inproceedings{Okazaki&Tsuji2010,
    title = "Simple and {E}fficient {A}lgorithm for {A}pproximate {D}ictionary {M}atching",
    author = "Okazaki, Naoaki  and Tsujii, Jun{'}ichi",
    booktitle = "Proceedings of the 23rd International Conference on Computational Linguistics (Coling 2010)",
    month = "August",
    year = "2010",
    address = "Beijing, China",
    publisher = "Coling 2010 Organizing Committee",
    url = "https://aclanthology.org/C10-1096",
    pages = "851--859",
}
```
- Soldaini and Goharian, 2016. QuickUMLS: a Fast, Unsupervised Approach for Medical Concept Extraction.
```bibtex
@misc{Soldaini&Goharian2016,
  title={Quick{UMLS}: a {F}ast, {U}nsupervised {A}pproach for {M}edical {C}oncept {E}xtraction},
  author={Luca Soldaini and Nazli Goharian},
  year={2016},
  url={https://ir.cs.georgetown.edu/downloads/quickumls.pdf}
}
```
- Corrêa Dias et al. 2021. Visual Exploration of Randomized Clinical Trials for COVID-19. In Proceedings of the BioCreative VII Challenge Evaluation Workshop.
```bibtex
@inproceedings{CorreaDias+2021,
    title = "Visual {E}xploration of {R}andomized {C}linical {T}rials for {COVID}-19",
    author = "Abel Corrêa Dias and Felipe M. F. Pontes and Viviane P. Moreira and João Luiz Dihl Comba",
    booktitle = "Proceedings of the BioCreative VII Challenge Evaluation Workshop",
    month = "November",
    year = "2021",
    isbn = "978-0-578-32368-8",
    url = "https://biocreative.bioinformatics.udel.edu/media/store/files/2021/Posters_pos_2_BC7_CorreaDias.pdf"
}
```
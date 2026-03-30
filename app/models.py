from . import db

# Table d'association pour gérer la relation "Plusieurs-à-Plusieurs" des prérequis
# Un sous-domaine peut avoir plusieurs prérequis, et être le prérequis de plusieurs autres.
prerequisites = db.Table('prerequisites',
    db.Column('subdomain_id', db.Integer, db.ForeignKey('sub_domain.id'), primary_key=True),
    db.Column('prerequisite_id', db.Integer, db.ForeignKey('sub_domain.id'), primary_key=True)
)

class Domain(db.Model):
    """Regroupe un domaine d'apprentissage (ex: Photographie, Python)."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    
    # Relation vers les sous-domaines
    sub_domains = db.relationship('SubDomain', backref='parent_domain', lazy=True, cascade="all, delete-orphan")

class SubDomain(db.Model):
    """Représente une étape ou un sous-sujet spécifique."""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    is_learned = db.Column(db.Boolean, default=False)
    domain_id = db.Column(db.Integer, db.ForeignKey('domain.id'), nullable=False)

    # La relation d'auto-référence pour les prérequis
    depends_on = db.relationship(
        'SubDomain', 
        secondary=prerequisites,
        primaryjoin=(prerequisites.c.subdomain_id == id),
        secondaryjoin=(prerequisites.c.prerequisite_id == id),
        backref='required_for' # Permet de voir quels sujets débloquent celui-ci
    )

    def can_be_learned(self):
        """Vérifie si tous les prérequis sont marqués comme 'appris'."""
        return all(pre.is_learned for pre in self.depends_on)
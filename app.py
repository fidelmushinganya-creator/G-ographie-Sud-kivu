from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_from_directory
)

from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

from database import get_db, init_db

import os
import uuid


app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "geographie-sud-kivu-cle-secrete-2026"
)


# ==========================================================
# CONFIGURATION
# ==========================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "uploads"
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

os.makedirs(
    os.path.join(UPLOAD_FOLDER, "cartes"),
    exist_ok=True
)

os.makedirs(
    os.path.join(UPLOAD_FOLDER, "articles"),
    exist_ok=True
)

os.makedirs(
    os.path.join(UPLOAD_FOLDER, "vocaux"),
    exist_ok=True
)

os.makedirs(
    os.path.join(UPLOAD_FOLDER, "annonces"),
    exist_ok=True
)
init_db()


# ==========================================================
# ACCUEIL
# ==========================================================

@app.route("/")
def accueil():

    return render_template(
        "index.html"
    )


# ==========================================================
# FICHIERS UPLOADÉS
# ==========================================================

@app.route("/uploads/<path:filename>")
def serve_upload(filename):

    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )


# ==========================================================
# CONNEXION ADMIN
# ==========================================================

@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        conn = get_db()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
            AND role = 'admin'
            """,
            (username,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session.clear()

            session["admin_id"] = user["id"]

            session["admin_username"] = user["username"]

            return redirect(
                url_for("admin_dashboard")
            )

        return render_template(
            "admin/login.html",
            error="Nom d'utilisateur ou mot de passe incorrect."
        )

    return render_template(
        "admin/login.html"
    )


# ==========================================================
# PROTECTION ADMIN
# ==========================================================

def admin_required():

    return "admin_id" in session


# ==========================================================
# TABLEAU DE BORD
# ==========================================================

@app.route("/admin/dashboard")
def admin_dashboard():

    if not admin_required():

        return redirect(
            url_for("admin_login")
        )


    search = request.args.get(
        "q",
        ""
    ).strip()


    selected_type = request.args.get(
        "type",
        ""
    ).strip()


    conn = get_db()


    # ------------------------------------------------------
    # PUBLICATIONS
    # ------------------------------------------------------

    query = """
        SELECT *
        FROM publications
        WHERE 1 = 1
    """

    params = []


    if search:

        query += """
            AND (
                title LIKE ?
                OR content LIKE ?
            )
        """

        search_value = f"%{search}%"

        params.extend([
            search_value,
            search_value
        ])


    if selected_type in [
        "carte",
        "article",
        "annonce"
    ]:

        query += """
            AND type = ?
        """

        params.append(
            selected_type
        )


    query += """
        ORDER BY created_at DESC
    """


    publications = conn.execute(
        query,
        params
    ).fetchall()


    # ------------------------------------------------------
    # STATISTIQUES
    # ------------------------------------------------------

    total_publications = conn.execute(
        """
        SELECT COUNT(*)
        AS total
        FROM publications
        """
    ).fetchone()["total"]


    total_comments = conn.execute(
        """
        SELECT COUNT(*)
        AS total
        FROM comments
        """
    ).fetchone()["total"]


    total_reactions = conn.execute(
        """
        SELECT COUNT(*)
        AS total
        FROM reactions
        """
    ).fetchone()["total"]


    total_users = conn.execute(
        """
        SELECT COUNT(*)
        AS total
        FROM users
        """
    ).fetchone()["total"]


    # ------------------------------------------------------
    # COMMENTAIRES
    # ------------------------------------------------------

    comments = conn.execute(
        """
        SELECT
            c.*,
            p.title AS publication_title,

            (
                SELECT r.content
                FROM replies r
                WHERE r.comment_id = c.id
                ORDER BY r.created_at DESC
                LIMIT 1
            ) AS reply_content

        FROM comments c

        LEFT JOIN publications p
            ON c.publication_id = p.id

        ORDER BY c.created_at DESC
        """
    ).fetchall()


    # ------------------------------------------------------
    # RÉACTIONS
    # ------------------------------------------------------

    reactions = conn.execute(
        """
        SELECT
            r.*,
            p.title AS publication_title,
            u.username

        FROM reactions r

        LEFT JOIN publications p
            ON r.publication_id = p.id

        LEFT JOIN users u
            ON r.user_id = u.id

        ORDER BY r.created_at DESC
        """
    ).fetchall()


    conn.close()


    return render_template(
        "admin/dashboard.html",

        username=session.get(
            "admin_username"
        ),

        publications=publications,

        comments=comments,

        reactions=reactions,

        total_publications=total_publications,

        total_comments=total_comments,

        total_reactions=total_reactions,

        total_users=total_users,

        search=search,

        selected_type=selected_type
    )


# ==========================================================
# PUBLIER
# ==========================================================

# ==========================================================
# PUBLIER
# ==========================================================

@app.route(
    "/admin/publier",
    methods=["GET", "POST"]
)
def publier():

    if not admin_required():

        return redirect(
            url_for("admin_login")
        )


    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()


        content = request.form.get(
            "content",
            ""
        ).strip()


        publication_type = request.form.get(
            "type",
            ""
        ).strip().lower()


        image = request.files.get(
            "image"
        )


        # --------------------------------------------------
        # VALIDATION DU TYPE
        # --------------------------------------------------

        types_autorises = [
            "carte",
            "article",
            "annonce"
        ]


        if publication_type not in types_autorises:

            return render_template(
                "admin/publier.html",
                error="Veuillez choisir une Carte, un Article ou une Annonce.",
                selected_type=publication_type
            )


        # --------------------------------------------------
        # VALIDATION DU TITRE
        # --------------------------------------------------

        if not title:

            return render_template(
                "admin/publier.html",
                error="Le titre est obligatoire.",
                selected_type=publication_type
            )


        # --------------------------------------------------
        # VALIDATION DU CONTENU
        # --------------------------------------------------

        if not content:

            return render_template(
                "admin/publier.html",
                error="Le contenu ou la description est obligatoire.",
                selected_type=publication_type
            )


        # --------------------------------------------------
        # CARTE : IMAGE OBLIGATOIRE
        # --------------------------------------------------

        if publication_type == "carte":

            if not image or not image.filename:

                return render_template(
                    "admin/publier.html",
                    error="Une image est obligatoire pour publier une carte.",
                    selected_type=publication_type
                )


        # --------------------------------------------------
        # GESTION DE L'IMAGE
        # --------------------------------------------------

        filename = None


        if image and image.filename:

            original_name = secure_filename(
                image.filename
            )


            extension = os.path.splitext(
                original_name
            )[1].lower()


            extensions_autorisees = [
                ".jpg",
                ".jpeg",
                ".png",
                ".webp",
                ".gif"
            ]


            if extension not in extensions_autorisees:

                return render_template(
                    "admin/publier.html",
                    error="Format d'image non autorisé. Utilisez JPG, JPEG, PNG, WEBP ou GIF.",
                    selected_type=publication_type
                )


            # ------------------------------------------------
            # NOM UNIQUE DE L'IMAGE
            # ------------------------------------------------

            filename_only = (
                str(uuid.uuid4())
                + extension
            )


            # ------------------------------------------------
            # DOSSIER SELON LE TYPE
            # ------------------------------------------------

            if publication_type == "carte":

                folder_name = "cartes"


            elif publication_type == "article":

                folder_name = "articles"


            else:

                folder_name = "annonces"


            folder = os.path.join(
                UPLOAD_FOLDER,
                folder_name
            )


            os.makedirs(
                folder,
                exist_ok=True
            )


            # ------------------------------------------------
            # ENREGISTREMENT PHYSIQUE
            # ------------------------------------------------

            image_path = os.path.join(
                folder,
                filename_only
            )


            image.save(
                image_path
            )


            # Chemin enregistré dans SQLite
            filename = os.path.join(
                folder_name,
                filename_only
            )


        # --------------------------------------------------
        # ENREGISTREMENT DANS LA BASE
        # --------------------------------------------------

        conn = get_db()


        conn.execute(
            """
            INSERT INTO publications
            (
                title,
                content,
                type,
                image
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                title,
                content,
                publication_type,
                filename
            )
        )


        conn.commit()

        conn.close()


        # --------------------------------------------------
        # MESSAGE DE SUCCÈS
        # --------------------------------------------------

        if publication_type == "carte":

            message = "🗺️ Carte publiée avec succès."


        elif publication_type == "article":

            message = "📚 Article publié avec succès."


        else:

            message = "📢 Annonce publiée avec succès."


        flash(
            message,
            "success"
        )


        return redirect(
            url_for("admin_dashboard")
        )


    # ------------------------------------------------------
    # AFFICHAGE DU FORMULAIRE
    # ------------------------------------------------------

    selected_type = request.args.get(
        "type",
        ""
    ).strip().lower()


    if selected_type not in [
        "carte",
        "article",
        "annonce"
    ]:

        selected_type = ""


    return render_template(
        "admin/publier.html",
        selected_type=selected_type
    )
@app.route(
    "/publication/<int:publication_id>"
)

# ==========================================================
# MODIFIER UNE PUBLICATION
# ==========================================================

@app.route(
    "/admin/modifier/<int:publication_id>",
    methods=["GET", "POST"]
)
def modifier_publication(
    publication_id
):

    if not admin_required():

        return redirect(
            url_for("admin_login")
        )


    conn = get_db()


    publication = conn.execute(
        """
        SELECT *
        FROM publications
        WHERE id = ?
        """,
        (publication_id,)
    ).fetchone()


    if not publication:

        conn.close()

        flash(
            "Publication introuvable.",
            "error"
        )

        return redirect(
            url_for("admin_dashboard")
        )


    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()


        content = request.form.get(
            "content",
            ""
        ).strip()


        publication_type = request.form.get(
            "type",
            ""
        ).strip()


        if not title or not content:

            conn.close()

            return render_template(
                "admin/publier.html",
                publication=publication,
                error="Le titre et le contenu sont obligatoires."
            )


        if publication_type not in [
            "carte",
            "article",
            "annonce"
        ]:

            conn.close()

            return render_template(
                "admin/publier.html",
                publication=publication,
                error="Type de publication invalide."
            )


        conn.execute(
            """
            UPDATE publications

            SET
                title = ?,
                content = ?,
                type = ?,
                updated_at = CURRENT_TIMESTAMP

            WHERE id = ?
            """,
            (
                title,
                content,
                publication_type,
                publication_id
            )
        )


        conn.commit()

        conn.close()


        flash(
            "Publication modifiée avec succès.",
            "success"
        )


        return redirect(
            url_for("admin_dashboard")
        )


    conn.close()


    return render_template(
        "admin/publier.html",
        publication=publication,
        mode="modifier"
    )
# ==========================================================
# GALERIE DES CARTES
# ==========================================================

    "/publication/<int:publication_id>"@app.route("/cartes")
def cartes():

    conn = get_db()

    publications = conn.execute(
        """
        SELECT *
        FROM publications
        WHERE type = 'carte'
        ORDER BY created_at DESC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "cartes.html",
        publications=publications
    )

# ==========================================================
# CARTES PUBLIQUES
# ==========================================================

@app.route("/cartes")
def cartes():

    conn = get_db()

    publications = conn.execute(
        """
        SELECT *
        FROM publications
        WHERE type = 'carte'
        ORDER BY created_at DESC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "cartes.html",
        publications=publications
    )

# ==========================================================
# ARTICLES
# ==========================================================

@app.route("/articles")
def articles():

    conn = get_db()

    publications = conn.execute(
        """
        SELECT *
        FROM publications
        WHERE type = 'article'
        ORDER BY created_at DESC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "articles.html",
        publications=publications
    )


# ==========================================================
# ANNONCES
# ==========================================================

@app.route("/annonces")
def annonces():

    conn = get_db()

    publications = conn.execute(
        """
        SELECT *
        FROM publications
        WHERE type = 'annonce'
        ORDER BY created_at DESC
        """
    ).fetchall()

    conn.close()

    return render_template(
        "annonces.html",
        publications=publications
    )
# ==========================================================
# VOIR UNE PUBLICATION
# ==========================================================
@app.route("/publication/<int:publication_id>")
def publication_detail(publication_id):

    conn = get_db()

    publication = conn.execute(
        """
        SELECT *
        FROM publications
        WHERE id = ?
        """,
        (publication_id,)
    ).fetchone()

    if not publication:
        conn.close()
        return "Publication introuvable", 404

    comments = conn.execute(
        """
        SELECT *
        FROM comments
        WHERE publication_id = ?
        ORDER BY created_at DESC
        """,
        (publication_id,)
    ).fetchall()

    # Récupérer les réponses de chaque commentaire
    comments_with_replies = []

    for comment in comments:

        replies = conn.execute(
            """
            SELECT *
            FROM replies
            WHERE comment_id = ?
            ORDER BY created_at ASC
            """,
            (comment["id"],)
        ).fetchall()

        comment_data = dict(comment)
        comment_data["replies"] = replies

        comments_with_replies.append(comment_data)

    conn.close()

    return render_template(
        "publication.html",
        publication=publication,
        comments=comments_with_replies
    )
# ==========================================================
# COMMENTER UNE PUBLICATION
# ==========================================================

@app.route(
    "/publication/<int:publication_id>/commenter",
    methods=["POST"]
)
def commenter_publication(publication_id):

    conn = get_db()

    publication = conn.execute(
        """
        SELECT id
        FROM publications
        WHERE id = ?
        """,
        (publication_id,)
    ).fetchone()

    if not publication:
        conn.close()
        return "Publication introuvable", 404

    author_name = request.form.get(
        "author_name",
        ""
    ).strip()

    content = request.form.get(
        "content",
        ""
    ).strip()

    if not author_name:
        conn.close()
        flash(
            "Veuillez entrer votre nom.",
            "error"
        )
        return redirect(
            url_for(
                "publication_detail",
                publication_id=publication_id
            )
        )

    if not content:
        conn.close()
        flash(
            "Votre commentaire est vide.",
            "error"
        )
        return redirect(
            url_for(
                "publication_detail",
                publication_id=publication_id
            )
        )

    conn.execute(
        """
        INSERT INTO comments
        (
            publication_id,
            author_name,
            content
        )
        VALUES (?, ?, ?)
        """,
        (
            publication_id,
            author_name,
            content
        )
    )

    conn.commit()
    conn.close()

    flash(
        "💬 Commentaire publié avec succès.",
        "success"
    )

    return redirect(
        url_for(
            "publication_detail",
            publication_id=publication_id
        ) + "#commentaires"
    )
# ==========================================================
# RÉPONDRE À UN COMMENTAIRE
# ==========================================================

@app.route(
    "/commentaire/<int:comment_id>/repondre",
    methods=["POST"]
)
def repondre_commentaire_public(comment_id):
    author_name = request.form.get(
        "author_name",
        ""
    ).strip()

    content = request.form.get(
        "content",
        ""
    ).strip()

    if not author_name:
        flash(
            "Veuillez entrer votre nom.",
            "error"
        )

        return redirect(
            request.referrer or url_for("index")
        )

    if not content:
        flash(
            "Votre réponse est vide.",
            "error"
        )

        return redirect(
            request.referrer or url_for("index")
        )

    conn = get_db()

    comment = conn.execute(
        """
        SELECT id, publication_id
        FROM comments
        WHERE id = ?
        """,
        (comment_id,)
    ).fetchone()

    if not comment:
        conn.close()
        return "Commentaire introuvable", 404

    conn.execute(
        """
        INSERT INTO replies
        (
            comment_id,
            author_name,
            content
        )
        VALUES (?, ?, ?)
        """,
        (
            comment_id,
            author_name,
            content
        )
    )

    conn.commit()
    publication_id = comment["publication_id"]

    conn.close()

    flash(
        "↩️ Réponse publiée avec succès.",
        "success"
    )

    return redirect(
        url_for(
            "publication_detail",
            publication_id=publication_id
        )
        + "#commentaires"
    )
# ==========================================================
# SUPPRIMER PUBLICATION
# ==========================================================

@app.route(
    "/admin/supprimer/<int:publication_id>",
    methods=["POST"]
)
def supprimer_publication(
    publication_id
):
    if not admin_required():

        return redirect(
            url_for("admin_login")
        )


    conn = get_db()


    publication = conn.execute(
        """
        SELECT *
        FROM publications
        WHERE id = ?
        """,
        (publication_id,)
    ).fetchone()


    if publication:

        # Réponses
        conn.execute(
            """
            DELETE FROM replies

            WHERE comment_id IN (

                SELECT id
                FROM comments
                WHERE publication_id = ?

            )
            """,
            (publication_id,)
        )


        # Commentaires
        conn.execute(
            """
            DELETE FROM comments
            WHERE publication_id = ?
            """,
            (publication_id,)
        )


        # Réactions
        conn.execute(
            """
            DELETE FROM reactions
            WHERE publication_id = ?
            """,
            (publication_id,)
        )


        # Publication
        conn.execute(
            """
            DELETE FROM publications
            WHERE id = ?
            """,
            (publication_id,)
        )


        conn.commit()


    conn.close()


    flash(
        "Publication supprimée.",
        "success"
    )


    return redirect(
        url_for("admin_dashboard")
    )


# ==========================================================
# RÉPONDRE À UN COMMENTAIRE
# ==========================================================

@app.route(
    "/admin/commentaire/<int:comment_id>/repondre",
    methods=["POST"]
)
def repondre_commentaire(
    comment_id
):

    if not admin_required():

        return redirect(
            url_for("admin_login")
        )


    content = request.form.get(
        "content",
        ""
    ).strip()


    if not content:

        flash(
            "La réponse ne peut pas être vide.",
            "error"
        )

        return redirect(
            url_for("admin_dashboard")
        )


    conn = get_db()


    comment = conn.execute(
        """
        SELECT *
        FROM comments
        WHERE id = ?
        """,
        (comment_id,)
    ).fetchone()


    if not comment:

        conn.close()

        flash(
            "Commentaire introuvable.",
            "error"
        )

        return redirect(
            url_for("admin_dashboard")
        )


    conn.execute(
        """
        INSERT INTO replies
        (
            comment_id,
            user_id,
            author_name,
            content
        )

        VALUES (?, ?, ?, ?)
        """,
        (
            comment_id,
            session.get("admin_id"),
            session.get(
                "admin_username",
                "Administrateur"
            ),
            content
        )
    )


    conn.commit()

    conn.close()


    flash(
        "Réponse envoyée.",
        "success"
    )


    return redirect(
        url_for("admin_dashboard")
    )


# ==========================================================
# SUPPRIMER COMMENTAIRE
# ==========================================================

@app.route(
    "/admin/commentaire/<int:comment_id>/supprimer",
    methods=["POST"]
)
def supprimer_commentaire(
    comment_id
):

    if not admin_required():

        return redirect(
            url_for("admin_login")
        )


    conn = get_db()


    conn.execute(
        """
        DELETE FROM replies
        WHERE comment_id = ?
        """,
        (comment_id,)
    )


    conn.execute(
        """
        DELETE FROM comments
        WHERE id = ?
        """,
        (comment_id,)
    )


    conn.commit()

    conn.close()


    flash(
        "Commentaire supprimé.",
        "success"
    )


    return redirect(
        url_for("admin_dashboard")
    )


# ==========================================================
# SUPPRIMER RÉACTION
# ==========================================================

@app.route(
    "/admin/reaction/<int:reaction_id>/supprimer",
    methods=["POST"]
)
def supprimer_reaction(
    reaction_id
):

    if not admin_required():

        return redirect(
            url_for("admin_login")
        )


    conn = get_db()


    conn.execute(
        """
        DELETE FROM reactions
        WHERE id = ?
        """,
        (reaction_id,)
    )


    conn.commit()

    conn.close()


    flash(
        "Réaction supprimée.",
        "success"
    )


    return redirect(
        url_for("admin_dashboard")
    )


# ==========================================================
# DÉCONNEXION
# ==========================================================

@app.route("/admin/logout")
def admin_logout():

    session.clear()

    return redirect(
        url_for("admin_login")
    )


# ==========================================================
# LANCEMENT
# ==========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )

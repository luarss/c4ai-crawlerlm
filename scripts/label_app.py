import json
from pathlib import Path

import streamlit as st
from bs4 import BeautifulSoup
from pydantic import ValidationError

from src.schemas import SCHEMA_REGISTRY


class AnnotationLabeler:
    """Streamlit-based annotation labeling interface."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.candidates_dir = self.project_root / "data" / "seeds" / "candidates"

        # Initialize session state
        if "current_idx" not in st.session_state:
            st.session_state.current_idx = 0
        if "files" not in st.session_state:
            st.session_state.files = self._load_annotation_files()

    def _load_annotation_files(self):
        """Load all annotation files from candidates directory."""
        files = []
        for annotation_path in sorted(self.candidates_dir.glob("*_annotation.json")):
            fragment_id = annotation_path.stem.replace("_annotation", "")
            html_path = annotation_path.parent / f"{fragment_id}.html"
            metadata_path = annotation_path.parent / f"{fragment_id}.json"

            if html_path.exists() and metadata_path.exists():
                files.append(
                    {
                        "annotation_path": annotation_path,
                        "html_path": html_path,
                        "metadata_path": metadata_path,
                        "fragment_id": fragment_id,
                    }
                )
        return files

    def _has_todos(self, data):
        """Check if annotation contains TODO markers."""
        json_str = json.dumps(data)
        return "TODO" in json_str

    def _count_stats(self):
        """Count annotation statistics."""
        stats = {"total": len(st.session_state.files), "completed": 0, "incomplete": 0}

        for file_info in st.session_state.files:
            with open(file_info["annotation_path"]) as f:
                data = json.load(f)
                if self._has_todos(data):
                    stats["incomplete"] += 1
                else:
                    stats["completed"] += 1

        return stats

    def _render_html_preview(self, html_content):
        """Render HTML preview with BeautifulSoup formatting."""
        import streamlit.components.v1 as components

        soup = BeautifulSoup(html_content, "html.parser")

        # Tabs for different views
        tab1, tab2, tab3 = st.tabs(["🌐 Rendered HTML", "📝 Text Preview", "💻 Raw HTML"])

        with tab1:
            st.markdown("**Rendered HTML Preview:**")
            st.caption("This is how the HTML fragment appears when rendered")
            # Render the HTML in an iframe with scrolling
            components.html(html_content, height=600, scrolling=True)

        with tab2:
            # Extract text content for preview
            text = soup.get_text(separator="\n", strip=True)
            lines = [line for line in text.split("\n") if line.strip()]

            st.markdown("**Extracted Text Content:**")
            preview_text = "\n".join(lines[:100])
            if len(lines) > 100:
                preview_text += f"\n\n... ({len(lines) - 100} more lines)"
            st.text_area("Text", preview_text, height=500, disabled=True, label_visibility="collapsed")

        with tab3:
            st.markdown("**Raw HTML Source:**")
            # Pretty print the HTML for better readability
            pretty_html = soup.prettify()
            st.code(pretty_html, language="html", line_numbers=True)

    def _render_recipe_form(self, data, fragment_id):
        """Render form for recipe schema."""
        st.subheader("Recipe Annotation")

        name = st.text_input("Recipe Name*", value=data.get("name", ""), key=f"{fragment_id}_name")
        description = st.text_area("Description", value=data.get("description") or "", key=f"{fragment_id}_description")
        author = st.text_input("Author", value=data.get("author") or "", key=f"{fragment_id}_author")

        col1, col2, col3 = st.columns(3)
        with col1:
            prep_time = st.text_input(
                "Prep Time (e.g., '15 min')", value=data.get("prep_time") or "", key=f"{fragment_id}_prep_time"
            )
        with col2:
            cook_time = st.text_input("Cook Time", value=data.get("cook_time") or "", key=f"{fragment_id}_cook_time")
        with col3:
            total_time = st.text_input(
                "Total Time", value=data.get("total_time") or "", key=f"{fragment_id}_total_time"
            )

        servings = st.text_input(
            "Servings (e.g., '4 servings')", value=data.get("servings") or "", key=f"{fragment_id}_servings"
        )

        # Ingredients
        st.markdown("**Ingredients***")
        ingredients = data.get("ingredients", [])
        ingredient_count = st.number_input(
            "Number of ingredients",
            min_value=1,
            value=max(len(ingredients), 1),
            step=1,
            key=f"{fragment_id}_ingredient_count",
        )

        new_ingredients = []
        for i in range(ingredient_count):
            default_val = ingredients[i] if i < len(ingredients) else ""
            ingredient = st.text_input(f"Ingredient {i + 1}", value=default_val, key=f"{fragment_id}_ingredient_{i}")
            if ingredient:
                new_ingredients.append(ingredient)

        # Instructions
        st.markdown("**Instructions***")
        instructions = data.get("instructions", [])
        instruction_count = st.number_input(
            "Number of steps",
            min_value=1,
            value=max(len(instructions), 1),
            step=1,
            key=f"{fragment_id}_instruction_count",
        )

        new_instructions = []
        for i in range(instruction_count):
            default_val = instructions[i] if i < len(instructions) else ""
            instruction = st.text_area(
                f"Step {i + 1}", value=default_val, key=f"{fragment_id}_instruction_{i}", height=80
            )
            if instruction:
                new_instructions.append(instruction)

        # Rating (optional)
        st.markdown("**Rating (optional)**")
        col1, col2 = st.columns(2)

        # Handle different rating formats (dict, int, or None)
        rating_data = data.get("rating")
        if isinstance(rating_data, dict):
            default_score = rating_data.get("score", 0.0)
            default_count = rating_data.get("review_count", 0)
        elif isinstance(rating_data, (int, float)):
            default_score = float(rating_data)
            default_count = 0
        else:
            default_score = 0.0
            default_count = 0

        with col1:
            rating_score = st.number_input(
                "Rating Score (0-5)",
                min_value=0.0,
                max_value=5.0,
                value=default_score,
                step=0.1,
                key=f"{fragment_id}_rating_score",
            )
        with col2:
            review_count = st.number_input(
                "Review Count", min_value=0, value=default_count, step=1, key=f"{fragment_id}_review_count"
            )

        return {
            "type": "recipe",
            "name": name,
            "description": description if description else None,
            "author": author if author else None,
            "prep_time": prep_time if prep_time else None,
            "cook_time": cook_time if cook_time else None,
            "total_time": total_time if total_time else None,
            "servings": servings if servings else None,
            "ingredients": new_ingredients,
            "instructions": new_instructions,
            "rating": {"score": rating_score, "review_count": review_count}
            if rating_score > 0 or review_count > 0
            else None,
        }

    def _render_product_form(self, data, fragment_id):
        """Render form for product schema."""
        st.subheader("Product Annotation")

        name = st.text_input("Product Name*", value=data.get("name", ""), key=f"{fragment_id}_name")
        brand = st.text_input("Brand", value=data.get("brand") or "", key=f"{fragment_id}_brand")
        description = st.text_area("Description", value=data.get("description") or "", key=f"{fragment_id}_description")

        # Price
        st.markdown("**Price***")
        col1, col2, col3 = st.columns(3)
        with col1:
            current_price = st.number_input(
                "Current Price",
                min_value=0.0,
                value=data.get("price", {}).get("current", 0.0),
                step=0.01,
                key=f"{fragment_id}_current_price",
            )
        with col2:
            original_price = st.number_input(
                "Original Price (optional)", min_value=0.0, value=0.0, step=0.01, key=f"{fragment_id}_original_price"
            )
        with col3:
            currency = st.text_input(
                "Currency", value=data.get("price", {}).get("currency", "USD"), key=f"{fragment_id}_currency"
            )

        # Rating
        st.markdown("**Rating (optional)**")
        col1, col2 = st.columns(2)

        # Handle different rating formats (dict, int, or None)
        rating_data = data.get("rating")
        if isinstance(rating_data, dict):
            default_score = rating_data.get("score", 0.0)
            default_count = rating_data.get("review_count", 0)
        elif isinstance(rating_data, (int, float)):
            default_score = float(rating_data)
            default_count = 0
        else:
            default_score = 0.0
            default_count = 0

        with col1:
            rating_score = st.number_input(
                "Rating Score (0-5)",
                min_value=0.0,
                max_value=5.0,
                value=default_score,
                step=0.1,
                key=f"{fragment_id}_rating_score",
            )
        with col2:
            review_count = st.number_input(
                "Review Count", min_value=0, value=default_count, step=1, key=f"{fragment_id}_review_count"
            )

        availability = st.selectbox(
            "Availability",
            ["in_stock", "out_of_stock", "pre_order", "limited"],
            index=0
            if not data.get("availability")
            else ["in_stock", "out_of_stock", "pre_order", "limited"].index(data.get("availability")),
            key=f"{fragment_id}_availability",
        )

        image_url = st.text_input("Image URL", value=data.get("image_url") or "", key=f"{fragment_id}_image_url")

        return {
            "type": "product",
            "name": name,
            "brand": brand if brand else None,
            "price": {
                "current": current_price,
                "original": original_price if original_price > 0 else None,
                "currency": currency,
            },
            "rating": {"score": rating_score, "review_count": review_count}
            if rating_score > 0 or review_count > 0
            else None,
            "description": description if description else None,
            "availability": availability,
            "image_url": image_url if image_url else None,
        }

    def _render_review_form(self, data, fragment_id):
        """Render form for review schema."""
        st.subheader("Review Annotation")

        reviewer_name = st.text_input(
            "Reviewer Name*", value=data.get("reviewer_name", ""), key=f"{fragment_id}_reviewer_name"
        )
        reviewer_verified = st.checkbox(
            "Verified Reviewer", value=data.get("reviewer_verified") or False, key=f"{fragment_id}_reviewer_verified"
        )

        rating = st.slider(
            "Rating*",
            min_value=0.0,
            max_value=5.0,
            value=data.get("rating", 0.0),
            step=0.5,
            key=f"{fragment_id}_rating",
        )

        title = st.text_input("Review Title", value=data.get("title") or "", key=f"{fragment_id}_title")
        date = st.text_input("Date*", value=data.get("date", ""), key=f"{fragment_id}_date")
        body = st.text_area("Review Body*", value=data.get("body", ""), height=200, key=f"{fragment_id}_body")

        helpful_count = st.number_input(
            "Helpful Count",
            min_value=0,
            value=data.get("helpful_count") or 0,
            step=1,
            key=f"{fragment_id}_helpful_count",
        )

        return {
            "type": "review",
            "reviewer_name": reviewer_name,
            "reviewer_verified": reviewer_verified if reviewer_verified else None,
            "rating": rating,
            "title": title if title else None,
            "date": date,
            "body": body,
            "helpful_count": helpful_count if helpful_count > 0 else None,
        }

    def _validate_annotation(self, annotation_data):
        """Validate annotation against schema."""
        fragment_type = annotation_data.get("type")
        if not fragment_type or fragment_type not in SCHEMA_REGISTRY:
            return False, f"Unknown fragment type: {fragment_type}"

        schema_class = SCHEMA_REGISTRY[fragment_type]
        try:
            schema_class(**annotation_data)
            return True, "Validation successful!"
        except ValidationError as e:
            errors = "\n".join([f"• {err['loc'][0]}: {err['msg']}" for err in e.errors()])
            return False, f"Validation errors:\n{errors}"

    def run(self):
        """Run the Streamlit app."""
        st.set_page_config(
            page_title="Annotation Labeler",
            layout="wide",
            page_icon="🏷️",
            initial_sidebar_state="expanded",
        )

        # Header
        st.title("🏷️ Annotation Labeler")

        # Stats in sidebar
        with st.sidebar:
            st.header("Progress")
            stats = self._count_stats()
            st.metric("Total Annotations", stats["total"])
            st.metric("Completed", stats["completed"])
            st.metric("Incomplete", stats["incomplete"])

            if stats["total"] > 0:
                progress = stats["completed"] / stats["total"]
                st.progress(progress)
                st.caption(f"{progress * 100:.1f}% complete")

            st.divider()

            # Navigation
            st.header("Navigation")
            if st.button("⏮️ First"):
                st.session_state.current_idx = 0
                st.rerun()

            if st.button("⏪ Previous"):
                st.session_state.current_idx = max(0, st.session_state.current_idx - 1)
                st.rerun()

            st.markdown(f"**{st.session_state.current_idx + 1}** / {len(st.session_state.files)}")

            if st.button("⏩ Next"):
                st.session_state.current_idx = min(len(st.session_state.files) - 1, st.session_state.current_idx + 1)
                st.rerun()

            if st.button("⏭️ Last"):
                st.session_state.current_idx = len(st.session_state.files) - 1
                st.rerun()

            st.divider()

            # Jump to specific annotation
            st.header("Jump to")
            selected_idx = st.selectbox(
                "Select annotation",
                range(len(st.session_state.files)),
                index=st.session_state.current_idx,
                format_func=lambda i: f"{i + 1}. {st.session_state.files[i]['fragment_id']}",
            )
            if selected_idx != st.session_state.current_idx:
                st.session_state.current_idx = selected_idx
                st.rerun()

        # Main content
        if not st.session_state.files:
            st.warning("No annotation files found in data/seeds/candidates/")
            return

        current_file = st.session_state.files[st.session_state.current_idx]

        # Load current data
        with open(current_file["annotation_path"]) as f:
            annotation_data = json.load(f)

        with open(current_file["metadata_path"]) as f:
            metadata = json.load(f)

        with open(current_file["html_path"]) as f:
            html_content = f.read()

        # Display metadata
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**Fragment ID:** `{metadata['fragment_id']}`")
        with col2:
            st.markdown(f"**Type:** `{metadata['fragment_type']}`")
        with col3:
            has_todos = self._has_todos(annotation_data)
            status = "❌ Incomplete" if has_todos else "✅ Complete"
            st.markdown(f"**Status:** {status}")

        st.markdown(f"**Source URL:** [{metadata['source_url']}]({metadata['source_url']})")

        st.divider()

        # Two-column layout
        col1, col2 = st.columns([1, 1])

        with col1:
            st.header("HTML Fragment")
            self._render_html_preview(html_content)

        with col2:
            st.header("Annotation Form")

            # Render appropriate form based on type
            fragment_type = annotation_data.get("type")
            fragment_id = current_file["fragment_id"]
            if fragment_type == "recipe":
                updated_annotation = self._render_recipe_form(annotation_data, fragment_id)
            elif fragment_type == "product":
                updated_annotation = self._render_product_form(annotation_data, fragment_id)
            elif fragment_type == "review":
                updated_annotation = self._render_review_form(annotation_data, fragment_id)
            else:
                st.error(f"Unsupported fragment type: {fragment_type}")
                st.json(annotation_data)
                return

            # Validate button
            st.divider()
            col1, col2 = st.columns(2)

            with col1:
                if st.button("💾 Save", type="primary", use_container_width=True):
                    # Validate first
                    is_valid, message = self._validate_annotation(updated_annotation)

                    if is_valid:
                        # Save annotation
                        with open(current_file["annotation_path"], "w") as f:
                            json.dump(updated_annotation, f, indent=2)
                        st.success("✅ Annotation saved successfully!")
                        st.rerun()
                    else:
                        st.error(f"❌ Validation failed:\n{message}")

            with col2:
                if st.button("🔍 Validate Only", use_container_width=True):
                    is_valid, message = self._validate_annotation(updated_annotation)
                    if is_valid:
                        st.success(f"✅ {message}")
                    else:
                        st.error(f"❌ {message}")

            # Show current annotation JSON
            with st.expander("View Current Annotation JSON"):
                st.json(annotation_data)


def main():
    """Main entry point."""
    labeler = AnnotationLabeler()
    labeler.run()


if __name__ == "__main__":
    main()
